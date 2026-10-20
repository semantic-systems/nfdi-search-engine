from typing import Any, Dict, Iterable, List

from config import Config
from nfdi_search_engine.common.dates import parse_date
from nfdi_search_engine.common.formatting import remove_html_tags
from nfdi_search_engine.common.models.objects import Author, Dataset, Organization, thing
from sources.base import BaseSource
from sources.http_client import quote_term


class RDMC(BaseSource):
    """
    RDMC source adapter: fetches Research Data Management Containers from the
    NFDIxCS registry service and maps them to Dataset objects.
    """

    SOURCE = "RDMC"

    def fetch(self, search_term: str) -> Dict[str, Any] | None:
        """
        Fetch raw JSON from the RDMC registry search API using the given search term.
        """
        search_result = self.http.get_json(
            Config.DATA_SOURCES[self.SOURCE].get("search-endpoint", "")
            + quote_term(search_term)
        )
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response.
        """
        if not raw:
            return []

        hits = raw.get("items", [])
        total_hits = raw.get("total", len(hits))

        if int(total_hits) > 0:
            self.log_event(
                type="info",
                message=f"{self.SOURCE} - {total_hits} records matched; pulled top {len(hits)}",
            )

        return hits

    def _map_authors(self, hit: Dict[str, Any]) -> List[Author]:
        """
        Map the contributor list of a single hit to Author objects.
        """
        authors = []

        for contributor in hit.get("contributors", []):
            given_name = contributor.get("first_name", "").strip()
            family_name = contributor.get("last_name", "").strip()
            name = " ".join(filter(None, [given_name, family_name]))
            if not name:
                continue

            _author = Author()
            _author.additionalType = "Person"
            _author.name = name
            _author.givenName = given_name
            _author.familyName = family_name
            _author.identifier = contributor.get("orcid", "").replace(
                "https://orcid.org/", ""
            )
            _author.jobTitle = contributor.get("role", "")

            affiliation = contributor.get("affiliation", "")
            if affiliation:
                _author.affiliation.append(Organization(name=affiliation))

            author_source = thing(
                name=self.SOURCE,
                identifier=_author.identifier,
            )
            _author.source.append(author_source)
            authors.append(_author)

        return authors

    def _map_keywords(self, hit: Dict[str, Any]) -> List[str]:
        """
        Collect the keywords of a single hit, prefixed by its subject classification.

        The manifest carries the same keywords, but as a list on the search
        endpoint and as a joined string on the details endpoint, so the
        flattened field is read instead.
        """
        keywords = hit.get("keywords_raw", "").split(",")

        collected = []
        seen = set()
        for keyword in [hit.get("subject", "")] + keywords:
            keyword = keyword.strip()
            if keyword and keyword.lower() not in seen:
                collected.append(keyword)
                seen.add(keyword.lower())

        return collected

    def map_hit(self, hit: Dict[str, Any]) -> Dataset:
        """
        Map a single RDMC record to a Dataset from objects.py.
        """
        dataset = Dataset()

        dataset.name = hit.get("title", "")
        # the handle PID is stable across versions; the short external id is not
        dataset.identifier = hit.get("pid", "") or hit.get("external_id", "")
        dataset.url = hit.get("rdmc_url", "")
        dataset.description = remove_html_tags(hit.get("description", ""))
        dataset.abstract = dataset.description
        dataset.license = hit.get("license", "")
        dataset.version = hit.get("rdmc_version", "")

        if hit.get("has_software_resources"):
            dataset.additionalType = "SOFTWARE"
        elif hit.get("has_data_resources"):
            dataset.additionalType = "DATASET"
        else:
            dataset.additionalType = "RDMC"

        date_published = hit.get("created_at", "")
        if date_published:
            dataset.datePublished = parse_date(date_published)

        for keyword in self._map_keywords(hit):
            dataset.keywords.append(keyword)

        for author in self._map_authors(hit):
            dataset.author.append(author)

        _source = thing()
        _source.name = self.SOURCE
        # the details route resolves this back through get_resource()
        _source.identifier = hit.get("external_id", "")
        _source.url = hit.get("viewer_url", "") or dataset.url
        dataset.source.append(_source)

        return dataset

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch from the RDMC registry, extract hits, map them to Datasets,
        and append them to results.
        """
        raw = self.fetch(search_term)
        if raw is None:
            return

        hits = self.extract_hits(raw)
        resource_count = 0

        for hit in hits:
            dataset = self.map_hit(hit)
            if dataset:
                results["resources"].append(dataset)
                resource_count += 1

        self.log_event(
            type="info",
            message=f"{self.SOURCE} - mapped {resource_count} resources",
        )

    def get_resource(self, doi: str) -> Dataset | None:
        """
        Fetch detailed metadata for a single RDMC.

        The details route passes the source identifier here, which for this
        source is the registry's external id rather than a DOI.
        """
        base_url = Config.DATA_SOURCES[self.SOURCE].get("get-resource-endpoint", "")
        raw = self.http.get_json(base_url + quote_term(doi))

        if not raw:
            return None

        return self.map_hit(raw)


def search(search_term: str, results: dict, tracking=None) -> None:
    """
    Entrypoint to search RDMC containers.
    """
    RDMC(tracking).search(search_term, results)


def get_resource(doi: str, tracking=None) -> Dataset | None:
    """
    Entrypoint to retrieve RDMC container details.
    """
    return RDMC(tracking).get_resource(doi)
