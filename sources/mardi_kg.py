from string import Template
from typing import Any, Dict, Iterable, List

from config import Config
from nfdi_search_engine.common.dates import parse_date
from nfdi_search_engine.common.models.objects import Article, Author, Dataset, thing
from sources.base import BaseSource
from sources.http_client import HttpClient


class MaRDI(BaseSource):
    """
    Resolves a search term to MaRDI Knowledge Graph items
    through the portal entity search, enriches them over SPARQL, and maps them
    to Article and Dataset objects.

    The entity search matches labels and aliases, not full text.
    Otherwise, the portals full text search times out server side.
    """

    SOURCE = "MARDI KG"

    # the entity search returns at most 50 items per request
    MAX_RECORDS = 50

    # items of any other type, e.g. a journal or a research field, are skipped
    PUBLICATION_TYPES = {
        "scholarly article",
        "article",
        "publication",
        "book",
        "monograph",
        "conference paper",
        "preprint",
        "doctoral thesis",
    }
    RESOURCE_TYPES = {
        "dataset",
        "software",
        "algorithm",
        "computer program",
    }

    # grouped by item alone
    # a repeated statement would otherwise split the row
    ENRICHMENT_QUERY = Template("""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX wd: <https://portal.mardi4nfdi.de/entity/>
        PREFIX wdt: <https://portal.mardi4nfdi.de/prop/direct/>
        SELECT ?item
               (GROUP_CONCAT(DISTINCT ?typeLabel; separator="|") AS ?types)
               (MIN(?doiValue) AS ?doi)
               (MIN(?dateValue) AS ?date)
               (MIN(?journalLabel) AS ?journal)
               (MIN(?urlValue) AS ?url)
               (GROUP_CONCAT(DISTINCT ?authorName; separator="|") AS ?authors)
        WHERE {
            VALUES ?item { $items }
            OPTIONAL { ?item wdt:P31 ?instanceOf . ?instanceOf rdfs:label ?typeLabel . FILTER(LANG(?typeLabel) = "en") }
            OPTIONAL { ?item wdt:P27 ?doiValue }
            OPTIONAL { ?item wdt:P28 ?dateValue }
            OPTIONAL { ?item wdt:P104 ?urlValue }
            OPTIONAL { ?item wdt:P200 ?publishedIn . ?publishedIn rdfs:label ?journalLabel . FILTER(LANG(?journalLabel) = "en") }
            OPTIONAL { ?item wdt:P16 ?author . ?author rdfs:label ?authorName . FILTER(LANG(?authorName) = "en") }
            OPTIONAL { ?item wdt:P43 ?authorName }
        }
        GROUP BY ?item
    """)

    def __init__(self, tracking=None, http: HttpClient = None) -> None:
        # this source needs longer than the global timeout, see the config entry
        super().__init__(
            tracking,
            http or HttpClient(
                timeout=Config.DATA_SOURCES[self.SOURCE].get("request-timeout")
            ),
        )

    def fetch(self, search_term: str) -> Dict[str, Any]:
        """
        Fetch raw JSON from the MaRDI entity search using the given search term.
        """
        search_result = self.http.get_json(
            Config.DATA_SOURCES[self.SOURCE].get("search-endpoint", ""),
            params={
                "action": "wbsearchentities",
                "format": "json",
                "type": "item",
                "language": "en",
                "uselang": "en",
                "limit": min(
                    Config.NUMBER_OF_RECORDS_FOR_SEARCH_ENDPOINT, self.MAX_RECORDS
                ),
                "search": search_term,
            },
        )
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of matched items from the raw JSON response.
        """
        if not raw:
            return []

        hits = []
        for entity in raw.get("search", []):
            if not entity.get("id"):
                continue
            display = entity.get("display", {})
            hits.append({
                "id": entity["id"],
                "label": display.get("label", {}).get("value", ""),
                "description": display.get("description", {}).get("value", ""),
                "page_url": entity.get("url", ""),
            })

        if hits:
            self.log_event(
                type="info",
                message=f"{self.SOURCE} - {len(hits)} items matched",
            )

        return hits

    def _enrich(self, hits: List[Dict[str, Any]]) -> None:
        """
        Look the given hits up over SPARQL and merge the statements into them.
        """
        if not hits:
            return

        query = self.ENRICHMENT_QUERY.substitute(
            items=" ".join(f"wd:{hit['id']}" for hit in hits)
        )
        raw = self.http.get_json(
            Config.DATA_SOURCES[self.SOURCE].get("sparql-endpoint", ""),
            params={"format": "json", "query": " ".join(query.split())},
        )

        rows = {}
        for binding in raw.get("results", {}).get("bindings", []):
            item_id = binding.get("item", {}).get("value", "").rsplit("/", 1)[-1]
            rows[item_id] = {
                key: value.get("value", "")
                for key, value in binding.items()
                if value.get("value", "")
            }

        for hit in hits:
            hit.update(rows.get(hit["id"], {}))

    def _source_thing(self, hit: Dict[str, Any]) -> thing:
        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("id", "")
        _source.url = hit.get("page_url", "")
        return _source

    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single publication hit to an Article from objects.py.
        """
        publication = Article()

        publication.name = hit.get("label", "")
        publication.identifier = hit.get("doi", "")
        publication.url = hit.get("url", "") or hit.get("page_url", "")
        publication.description = hit.get("description", "")
        publication.abstract = publication.description
        publication.additionalType = hit.get("type", "")
        publication.publication = hit.get("journal", "")

        date_published = hit.get("date", "")
        if date_published:
            publication.datePublished = parse_date(date_published)

        for author_name in self._split(hit, "authors"):
            _author = Author()
            _author.additionalType = "Person"
            _author.name = author_name
            _author.source.append(thing(name=self.SOURCE))
            publication.author.append(_author)

        publication.source.append(self._source_thing(hit))

        return publication

    def map_dataset_hit(self, hit: Dict[str, Any]) -> Dataset:
        """
        Map a single dataset or software hit to a Dataset from objects.py.
        """
        dataset = Dataset()

        dataset.name = hit.get("label", "")
        dataset.identifier = hit.get("doi", "")
        dataset.url = hit.get("url", "") or hit.get("page_url", "")
        dataset.description = hit.get("description", "")
        dataset.abstract = dataset.description
        dataset.additionalType = hit.get("type", "")

        date_published = hit.get("date", "")
        if date_published:
            dataset.datePublished = parse_date(date_published)

        dataset.source.append(self._source_thing(hit))

        return dataset

    def _split(self, hit: Dict[str, Any], key: str) -> List[str]:
        """
        Split one of the grouped SPARQL fields of a hit back into its values.
        """
        return [part.strip() for part in hit.get(key, "").split("|") if part.strip()]

    def search(self, search_term: str, results: dict) -> None:
        """
        Fetch from MaRDI, enrich the hits in one SPARQL request, and append the
        mapped objects to the bucket their type belongs to.
        """
        raw = self.fetch(search_term)
        if raw is None:
            return

        hits = list(self.extract_hits(raw))
        if not hits:
            return

        self._enrich(hits)

        publication_count = 0
        resource_count = 0
        for hit in hits:
            item_types = {item_type.lower() for item_type in self._split(hit, "types")}
            publication_types = item_types & self.PUBLICATION_TYPES
            resource_types = item_types & self.RESOURCE_TYPES

            # sorted, so an item stating several types always maps the same way
            if publication_types:
                hit["type"] = sorted(publication_types)[0]
                results["publications"].append(self.map_hit(hit))
                publication_count += 1
            elif resource_types:
                hit["type"] = sorted(resource_types)[0]
                results["resources"].append(self.map_dataset_hit(hit))
                resource_count += 1

        self.log_event(
            type="info",
            message=(
                f"{self.SOURCE} - mapped {publication_count} publications "
                f"and {resource_count} resources"
            ),
        )


def search(search_term: str, results: dict, tracking=None) -> None:
    """
    Entrypoint to search the MaRDI Knowledge Graph.
    """
    MaRDI(tracking).search(search_term, results)
