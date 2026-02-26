import re
from typing import Iterable, Dict, Any

from objects import thing, Article, Author
from sources import data_retriever
from sources.base import BaseSource
from main import app

import utils


class Resodate(BaseSource):
    """
    Resodate source adapter: fetches OER data from resodate.org search API,
    maps Elasticsearch-style hits to Article objects.
    """

    SOURCE = "resodate"

    @utils.handle_exceptions
    def fetch(self, search_term: str, failed_sources: list) -> Dict[str, Any] | None:
        """
        Fetch raw JSON from the Resodate search API using the given search term.
        """
        search_result = data_retriever.retrieve_data(
            source=self.SOURCE,
            base_url=app.config["DATA_SOURCES"][self.SOURCE].get("search-endpoint", ""),
            search_term=search_term,
            failed_sources=failed_sources,
        )
        return search_result

    @utils.handle_exceptions
    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw Elasticsearch-style JSON response.
        """
        if raw is None:
            return []

        hits_container = raw.get("hits", {})
        total_info = hits_container.get("total", 0)
        if isinstance(total_info, dict):
            total_hits = total_info.get("value", 0)
        else:
            total_hits = total_info

        hits = hits_container.get("hits", [])

        if int(total_hits) > 0:
            utils.log_event(
                type="info",
                message=f"{self.SOURCE} - {total_hits} records matched; pulled top {len(hits)}",
            )

        return hits

    @utils.handle_exceptions
    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single hit (with _source and _id) to an Article from objects.py.
        """
        hit_source = hit.get("_source", {})

        publication = Article()
        publication.name = hit_source.get("name", "")
        publication.url = hit_source.get("id", "")
        publication.identifier = re.sub(
            r"^.*doi\.org/", "", hit_source.get("id", "")
        )
        publication.datePublished = hit_source.get("datePublished", "")
        if publication.datePublished:
            publication.datePublished = utils.parse_date(publication.datePublished)
        publication.license = hit_source.get("license", {}).get("id", "")

        publication.description = utils.remove_html_tags(
            hit_source.get("description", "")
        )
        publication.abstract = publication.description

        publishers = hit_source.get("publisher", [])
        if publishers:
            publication.publication = publishers[0].get("name", "")

        for author in hit_source.get("creator", []):
            if author.get("type") == "Person":
                _author = Author()
                _author.additionalType = "Person"
                _author.name = author.get("name", "")
                _author.identifier = author.get("id", "").replace(
                    "https://orcid.org/", ""
                )
                author_source = thing(
                    name=self.SOURCE,
                    identifier=_author.identifier,
                )
                _author.source.append(author_source)
                publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("_id", "")
        _source.url = "https://resodate.org/resources/" + hit.get("_id", "")
        publication.source.append(_source)

        publication.image = hit_source.get("image", "")

        keywords = hit_source.get("keywords")
        if keywords:
            for keyword in keywords:
                publication.keywords.append(keyword)

        languages = hit_source.get("inLanguage")
        if languages:
            for language in languages:
                publication.inLanguage.append(language)

        encodings = hit_source.get("encoding")
        if encodings:
            for encoding in encodings:
                publication.encoding_contentUrl = encoding.get("contentUrl", "")
                publication.encodingFormat = encoding.get("encodingFormat", "")

        return publication

    @utils.handle_exceptions
    def search(
        self,
        source_name: str,
        search_term: str,
        results: dict,
        failed_sources: list,
    ) -> None:
        """
        Fetch from Resodate, extract hits, map to Articles, and append to results.
        """
        raw = self.fetch(search_term, failed_sources)
        if raw is None:
            return

        hits = self.extract_hits(raw)
        for hit in hits:
            publication = self.map_hit(hit)
            results["publications"].append(publication)


@utils.handle_exceptions
def search(
    source: str,
    search_term: str,
    results: dict,
    failed_sources: list,
) -> None:
    """
    Entrypoint to search Resodate publications.
    """
    Resodate().search(source, search_term, results, failed_sources)
