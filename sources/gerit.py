import json
import os

from typing import Any, Dict, Iterable, List, Tuple

from config import Config
from nfdi_search_engine.common.models.objects import Organization, thing
from sources.base import BaseSource


class GERiT(BaseSource):
    """
    Resolves a search term to German research institutions and maps them to
    Organization objects.

    GERiT has no search API, so the institutions are read from the local JSON
    file that is updated by the gerit.refresh job.
    """

    SOURCE = "GERiT"

    MATCH_FIELDS = (
        "name_deutsch",
        "name_englisch",
        "ort",
        "einrichtungsart",
        "einrichtungsart_englisch",
    )
    SUBJECT_FIELDS = (
        "destatis_faechergruppe_englisch",
        "destatis_lehr_forschungsbereich_englisch",
        "destatis_fachgebiet_englisch",
    )

    # the records are shared, so a search does not parse the file again
    _cache: Tuple[float, List[Dict[str, str]]] = None

    def _records(self) -> List[Dict[str, str]]:
        """
        Load the institutions, reusing them while the local file is unchanged.
        """
        path = Config.DATA_SOURCES[self.SOURCE].get("local-path", "")

        try:
            modified_at = os.path.getmtime(path)
        except OSError:
            # the refresh job has not run yet, see its worker_ready handler
            self.log_event(
                type="warning",
                message=f"{self.SOURCE} - no local data at {path}",
            )
            return []

        if GERiT._cache and GERiT._cache[0] == modified_at:
            return GERiT._cache[1]

        with open(path, encoding="utf-8") as file:
            records = json.load(file)

        GERiT._cache = (modified_at, records)
        return records

    def fetch(self, search_term: str) -> List[Dict[str, str]]:
        """
        Read the institutions matching the search term by name, city or type.
        """
        term = search_term.lower()
        return [
            record for record in self._records()
            if any(term in record.get(field, "").lower() for field in self.MATCH_FIELDS)
        ]

    def extract_hits(self, raw: List[Dict[str, str]]) -> Iterable[Dict[str, str]]:
        """
        The local file holds one record per institution, so the matches are
        already the hits.
        """
        return raw

    def map_hit(self, hit: Dict[str, Any]) -> Organization:
        """
        Map a single institution record to an Organization from objects.py.
        """
        organization = Organization()

        organization.identifier = hit.get("dfg_inst_id", "")
        organization.name = hit.get("name_deutsch", "")
        organization.url = hit.get("url_der_einrichtung", "")
        organization.additionalType = (
            hit.get("einrichtungsart_englisch", "") or hit.get("einrichtungsart", "")
        )

        english_name = hit.get("name_englisch", "")
        if english_name:
            organization.alternateName.append(english_name)

        street = " ".join(filter(None, [hit.get("strasse", ""), hit.get("hausnummer", "")]))
        city = " ".join(filter(None, [hit.get("postleitzahl_vor_ort", ""), hit.get("ort", "")]))
        organization.address = ", ".join(filter(None, [street, city]))

        organization.keywords = self._keywords(hit)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = organization.identifier
        _source.url = hit.get("url_gerit_nachweis", "")
        organization.source.append(_source)

        return organization

    def _keywords(self, hit: Dict[str, Any]) -> List[str]:
        """
        Collect the identifiers and subject classifications shown as badges.
        """
        keywords = []

        for label, field in (("ROR", "ror_id"), ("Wikidata", "wikidata_id")):
            value = hit.get(field, "")
            if value:
                keywords.append(f"{label}: {value}")

        # the three levels repeat each other for institutions without a subject
        for field in self.SUBJECT_FIELDS:
            subject = hit.get(field, "")
            if subject and subject not in keywords:
                keywords.append(subject)

        return keywords

    def search(self, search_term: str, results: dict) -> None:
        """
        Read the local institutions and append every match to the results.
        """
        hits = list(self.extract_hits(self.fetch(search_term)))

        for hit in hits:
            results["organizations"].append(self.map_hit(hit))

        self.log_event(
            type="info",
            message=f"{self.SOURCE} - mapped {len(hits)} organizations",
        )


def search(search_term: str, results: dict, tracking=None) -> None:
    """
    Entrypoint to search GERiT institutions.
    """
    GERiT(tracking).search(search_term, results)
