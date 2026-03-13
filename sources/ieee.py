# sources/ieee.py

from nfdi_search_engine.common.models.objects import thing, Article, Author
from sources import data_retriever
from sources.base import BaseSource
from typing import Iterable, Dict, Any
from config import Config
from datetime import datetime
from dateutil import parser
from config import Config
from nfdi_search_engine.common.formatting import remove_html_tags


class IEEE(BaseSource):

    SOURCE = "IEEE"

    def fetch(self, search_term: str, failed_sources: list) -> Dict[str, Any]:
        """
        Fetch raw json from the source using the given search term.
        """
        base_url_template = Config.DATA_SOURCES[self.SOURCE].get("search-endpoint", "")
        if not base_url_template:
            self.log_event(type="error", message=f"{self.SOURCE} - No search endpoint configured")
            failed_sources.append(self.SOURCE)
            return None

        api_key = getattr(Config, "IEEE_API_KEY", "") or ""
        if not api_key.strip():
            self.log_event(type="error", message=f"{self.SOURCE} - IEEE_API_KEY is missing or empty")
            failed_sources.append(self.SOURCE)
            return None

        api_key_param = Config.DATA_SOURCES[self.SOURCE].get("api-key-param", "apikey")

        if "?" in base_url_template:
            base_url = base_url_template.replace("?", f"?{api_key_param}={api_key}&", 1)
        else:
            base_url = f"{base_url_template}?{api_key_param}={api_key}"

        search_result = data_retriever.retrieve_data(
            source=self.SOURCE,
            base_url=base_url,
            search_term=search_term,
            failed_sources=failed_sources,
        )
        return search_result

    def extract_hits(self, raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        """
        Extract the list of hits from the raw JSON response.
        """
        if raw is None:
            return []

        hits = raw.get("articles", [])

        total_records = raw.get("total_records", len(hits))
        try:
            total_records = int(total_records) if total_records is not None else len(hits)
        except (ValueError, TypeError):
            total_records = len(hits)

        if not hits:
            self.log_event(type="info", message=f"{self.SOURCE} - {total_records} records matched; pulled top 0")
            return []

        self.log_event(type="info", message=f"{self.SOURCE} - {total_records} records matched; pulled top {len(hits)}")
        return hits

    def map_hit(self, hit: Dict[str, Any]) -> Article:
        """
        Map a single hit dict from the source to an Article object.
        """
        publication = Article()

        publication.name = hit.get("title", "") or ""
        publication.url = hit.get("html_url", "") or ""
        publication.identifier = hit.get("doi", "") or ""

        publication_date = hit.get("publication_date", "") or ""
        if publication_date:
            try:
                publication.datePublished = datetime.strftime(parser.parse(publication_date), "%Y-%m-%d")
            except (ValueError, TypeError):
                publication.datePublished = ""
        else:
            insert_date = hit.get("insert_date", "") or ""
            if isinstance(insert_date, str) and len(insert_date) == 8 and insert_date.isdigit():
                publication.datePublished = f"{insert_date[:4]}-{insert_date[4:6]}-{insert_date[6:8]}"
            else:
                publication.datePublished = ""

        publication.license = hit.get("access_type", "") or ""
        publication.publication = hit.get("publisher", "") or ""

        abstract = hit.get("abstract", "") or ""
        publication.description = remove_html_tags(abstract)
        publication.abstract = publication.description

        publication.encoding_contentUrl = hit.get("pdf_url", "") or ""

        authors_data = hit.get("authors", {})
        if isinstance(authors_data, dict):
            authors = authors_data.get("authors", []) or []
        elif isinstance(authors_data, list):
            authors = authors_data
        else:
            authors = []

        for author in authors:
            if not isinstance(author, dict):
                continue
            _author = Author()
            _author.additionalType = "Person"
            _author.name = author.get("full_name", "") or ""
            _author.identifier = author.get("id", "") or ""

            author_source = thing(
                name=self.SOURCE,
                identifier=_author.identifier,
            )
            _author.source.append(author_source)
            publication.author.append(_author)

        _source = thing()
        _source.name = self.SOURCE
        _source.identifier = hit.get("article_number", "") or ""
        _source.url = publication.url
        publication.source.append(_source)

        return publication

    def search(self, source_name: str, search_term: str, results: dict, failed_sources: list) -> None:
        """
        Fetch json from the source, extract hits, map them to objects, and insert them into results dict.
        """
        raw = self.fetch(search_term, failed_sources)
        if raw is None:
            return

        hits = self.extract_hits(raw)
        for hit in hits:
            digitalObj = self.map_hit(hit)
            if digitalObj:
                results["publications"].append(digitalObj)

    def get_publication(self, doi: str) -> Article | None:
        """
        Fetch a single publication by DOI.
        """
        api_key = getattr(Config, "IEEE_API_KEY", "") or ""
        base_url_template = Config.DATA_SOURCES[self.SOURCE].get("get-publication-endpoint", "")

        if not api_key.strip() or not base_url_template:
            return None

        api_key_param = Config.DATA_SOURCES[self.SOURCE].get("api-key-param", "apikey")

        if "?" in base_url_template:
            base_url = base_url_template.replace("?", f"?{api_key_param}={api_key}&", 1)
        else:
            base_url = f"{base_url_template}?{api_key_param}={api_key}"

        search_result = data_retriever.retrieve_object(
            source=self.SOURCE,
            base_url=base_url,
            identifier=doi,
        )

        if not search_result:
            return None

        articles = search_result.get("articles", []) or []
        if not articles:
            return None

        return self.map_hit(articles[0])


def search(source: str, search_term: str, results, failed_sources, tracking=None):
    """
    Entrypoint to search IEEE publications.
    """
    IEEE(tracking).search(source, search_term, results, failed_sources)


def get_publication(source: str, doi: str, source_id: str, publications, tracking=None):
    """
    Entrypoint to get a single IEEE publication by DOI.
    """
    publication = IEEE(tracking).get_publication(doi)
    if publication:
        publications.append(publication)
