import json
import os
import re
from typing import Any, Dict, Iterable, List

import utils
from objects import Organization, thing
from sources.base import BaseSource


class GERiT(BaseSource):
    """
    Local-file source adapter for the GERiT institutions dataset.

    GERiT (German Research Institutions) is a DFG registry of research
    institutions in Germany. The dataset is published monthly as an .xlsx file
    and converted to JSON via sources/gerit/xlsx_to_json.py.
    """

    SOURCE = "GERiT"

    def fetch(self, search_term: str, failed_sources: list) -> List[Dict[str, Any]]:
        """Load all records from the local JSON file."""
        json_path = os.path.join(os.path.dirname(__file__), "gerit", "institutionen_gerit.json")
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            return data
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            utils.log_event(type="error", message=f"{self.SOURCE} - {exc}")
            failed_sources.append(self.SOURCE)
            return []

    def extract_hits(
        self, raw: List[Dict[str, Any]], search_term: str = ""
    ) -> Iterable[Dict[str, Any]]:
        """
        Filter records relevant to the search term.

        Name fields (DE/EN): any token appearing as a substring suffices (case-insensitive).
        DESTATIS fields: all tokens must match as whole words (stricter).
        """
        tokens = [t.lower() for t in search_term.split() if t]
        if not tokens:
            return []

        def name_match(record):
            haystack = " ".join(
                str(record.get(f) or "")
                for f in ("Name deutsch", "Name englisch")
            ).lower()
            return any(t in haystack for t in tokens)

        def destatis_match(record):
            haystack = " ".join(
                str(record.get(f) or "")
                for f in (
                    "DESTATIS Fächergruppe englisch",
                    "DESTATIS Lehr- Forschungsbereich englisch",
                    "DESTATIS Fachgebiet englisch",
                )
            ).lower()
            return all(re.search(rf"\b{re.escape(t)}\b", haystack) for t in tokens)

        hits = [r for r in raw if name_match(r) or destatis_match(r)]

        utils.log_event(
            type="info",
            message=f"{self.SOURCE} - {len(hits)} records matched for '{search_term}'",
        )
        return hits

    def map_hit(self, hit: Dict[str, Any]) -> Organization:
        """Map a single GERiT record to an Organization object."""
        org = Organization()

        name_en = str(hit["Name englisch"]).strip() if hit.get("Name englisch") else None
        name_de = str(hit["Name deutsch"]).strip() if hit.get("Name deutsch") else None
        org.name = name_en or name_de or ""
        if name_en and name_de:
            org.alternateName = [name_de]

        dfg_id = hit.get("DFG-Inst-ID")
        org.identifier = str(dfg_id) if dfg_id is not None else ""
        org.url = str(hit["URL der Einrichtung"]).strip() if hit.get("URL der Einrichtung") else ""
        org.additionalType = str(hit["Einrichtungsart englisch"]).strip() if hit.get("Einrichtungsart englisch") else ""

        address_parts = [
            str(hit[f]).strip()
            for f in ("Strasse", "Hausnummer", "Postleitzahl vor Ort", "Ort")
            if hit.get(f) is not None
        ]
        org.address = " ".join(address_parts)
        org.location = str(hit["Ort"]).strip() if hit.get("Ort") else ""

        seen = set()
        org.keywords = []
        for f in ("DESTATIS Fächergruppe englisch", "DESTATIS Lehr- Forschungsbereich englisch", "DESTATIS Fachgebiet englisch"):
            v = str(hit[f]).strip() if hit.get(f) is not None else None
            if v and v not in seen:
                org.keywords.append(v)
                seen.add(v)
        if hit.get("ROR-ID"):
            org.keywords.append(f"ROR: {str(hit['ROR-ID']).strip()}")
        if hit.get("Wikidata-ID"):
            org.keywords.append(f"Wikidata: {str(hit['Wikidata-ID']).strip()}")

        gerit_url = str(hit["URL GERiT Nachweis"]).strip() if hit.get("URL GERiT Nachweis") else ""
        org.originalSource = gerit_url
        org.source.append(thing(name=self.SOURCE, identifier=org.identifier, url=gerit_url))

        return org

    def search(
        self,
        source_name: str,
        search_term: str,
        results: dict,
        failed_sources: list,
    ) -> None:
        """Search GERiT and append matched Organization objects to results["organizations"]."""
        raw = self.fetch(search_term, failed_sources)
        hits = self.extract_hits(raw, search_term)
        for hit in hits:
            results["organizations"].append(self.map_hit(hit))


def search(source: str, search_term: str, results: dict, failed_sources: list) -> None:
    GERiT().search(source, search_term, results, failed_sources)
