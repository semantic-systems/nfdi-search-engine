# sources/semanticscholar_publications.py
"""
Semantic Scholar Publications source module.

Provides DOI-based lookups for citations and recommendations via the Semantic Scholar API.
This module does not implement search-by-term (BaseSource); it is used only for
publication-details citations and recommendations. Integration points: get_dois_citations,
get_citations_for_publication, get_recommendations_for_publication.
"""
import time
from typing import Any, Callable, Dict, List

import requests

from config import Config
from nfdi_search_engine.common.models.objects import thing, Article, Author
from sources import data_retriever
from nfdi_search_engine.common.formatting import remove_html_tags
from nfdi_search_engine.services.tracking_service import TrackingService

# Retry configuration for API rate limiting / transient failures
MAX_RETRIES = 10
RETRY_DELAY_SECONDS = 2


class SemanticScholarPublications:
    """
    Handles Semantic Scholar API calls for publication citations and recommendations by DOI.
    """

    SOURCE = "SEMANTIC SCHOLAR - Publications"

    def __init__(self, tracking: TrackingService = None):
        self.tracking = tracking

    def log_event(self, type: str, message: str):
        """
        Match the log_event signature used in sources.
        Async logging to elastic if TrackingService is passed in the constructor,
        to stdout otherwise.
        """
        if self.tracking is not None:
            self.tracking.log_event_async(
                log_type=type,
                message=message,
            )
        else:
            # if no tracking service is passed, log to stdout
            print(f"{type.upper()}: {self.SOURCE}: {message}")

    def _get_config(self, source: str, key: str, default: str = "") -> str:
        """Return config value for the given source and key."""
        return Config.DATA_SOURCES.get(source, {}).get(key, default)

    def get_dois_citations(self, doi: str) -> List[str]:
        """
        Fetch the DOIs of citations for a given DOI.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article to fetch citations for.

        Returns:
            A list of DOIs of the citing articles.
        """
        base_url = self._get_config(self.SOURCE, "citations-endpoint", "")
        identifier = f"{doi}?fields=citations.externalIds"
        response = data_retriever.retrieve_object(
            base_url=base_url,
            identifier=identifier,
            quote=False,
        )

        if not response or "citations" not in response:
            return []

        dois_citation = [
            citation.get("externalIds", {}).get("DOI", "")
            for citation in response["citations"]
        ]
        return [d for d in dois_citation if d]

    def _request_with_retries(self, fetch: Callable[[], Any], context: str) -> Dict[str, Any]:
        """
        Call ``fetch`` with retries, logging HTTP and parse errors.

        Returns the response dict, or None if it never succeeds. Client errors
        (4xx other than 429) are not retried, since retrying won't help and the
        fixed back-off would otherwise block the request for MAX_RETRIES * delay.

        :param fetch: Zero-arg callable performing the HTTP request.
        :param context: Human-readable label used in log messages.
        """
        for attempt in range(MAX_RETRIES):
            try:
                response = fetch()
            except requests.HTTPError as e:
                resp = e.response
                status = resp.status_code if resp is not None else "?"
                body = (resp.text[:300] if resp is not None else "").replace("\n", " ")
                self.log_event(
                    type="error",
                    message=f"{self.SOURCE} - {context} - HTTP {status}: {body}",
                )
                if resp is not None and 400 <= resp.status_code < 500 and resp.status_code != 429:
                    return None
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            except Exception as e:
                self.log_event(
                    type="error",
                    message=f"{self.SOURCE} - {context} - request failed: {e!r}",
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue

            if isinstance(response, dict):
                return response

            self.log_event(
                type="info",
                message=f"{self.SOURCE} - {context} - retry {attempt + 1}/{MAX_RETRIES} (non-dict response)",
            )
            time.sleep(RETRY_DELAY_SECONDS)

        self.log_event(
            type="error",
            message=f"{self.SOURCE} - {context} - gave up after {MAX_RETRIES} attempts",
        )
        return None

    def _fetch_paper_by_doi(self, doi: str) -> Dict[str, Any]:
        """
        Retrieve Semantic Scholar paper payload by DOI (with retries).
        Returns the raw response dict or None on failure.
        """
        base_url = self._get_config(self.SOURCE, "citations-endpoint", "")
        return self._request_with_retries(
            lambda: data_retriever.retrieve_object(
                base_url=base_url, identifier=doi, quote=False,
            ),
            context=f"resolve DOI->paperId ({doi})",
        )

    def _fetch_recommendations_by_paper_id(self, paper_id: str, limit: int = 100) -> Dict[str, Any]:
        """
        Retrieve recommendations for a paper by its Semantic Scholar paper ID (with retries).
        Returns the raw response dict or None on failure.

        Note: the recommendations endpoint does not support nested author field
        selection (e.g. ``authors.externalIds``), so ORCIDs are not available here.
        """
        base_url = self._get_config(self.SOURCE, "recommendations-endpoint", "")
        fields = "title,publicationDate,externalIds,authors,isOpenAccess,openAccessPdf"
        search_term = f"{paper_id}?fields={fields}&limit={limit}"
        return self._request_with_retries(
            lambda: data_retriever.retrieve_data(
                base_url=base_url, search_term=search_term,
            ),
            context=f"recommendations (paper_id={paper_id}, limit={limit})",
        )

    def get_recommendations_for_publication(self, doi: str, limit: int = 100) -> List[Article]:
        """
        Fetch recommended publications for a given DOI as Article objects.

        Resolves the DOI to a Semantic Scholar paper ID, then fetches recommendations.
        Only articles with a non-empty DOI are included. Each Article is populated
        with authors, publication date, source, and (when available) an open-access
        content URL so it can be rendered like a search result.

        Args:
            doi: The DOI of the article.
            limit: Maximum number of recommendations to request.

        Returns:
            List of Article objects for recommended publications.
        """
        recommended_publications: List[Article] = []

        paper_response = self._fetch_paper_by_doi(doi)
        if not paper_response:
            return recommended_publications

        paper_id = paper_response.get("paperId", "")
        if not paper_id:
            return recommended_publications

        self.log_event(
            type="info",
            message=f"{self.SOURCE} - Resolved DOI to Semantic Scholar paper_id: {paper_id}",
        )

        rec_response = self._fetch_recommendations_by_paper_id(paper_id, limit=limit)
        if not rec_response:
            return recommended_publications

        recommended_papers = rec_response.get("recommendedPapers", [])
        self.log_event(
            type="info",
            message=f"{self.SOURCE} - received {len(recommended_papers)} recommendations for paper_id {paper_id}",
        )
        for recommended_paper in recommended_papers:
            publication = Article()
            publication.name = remove_html_tags(
                recommended_paper.get("title", "")
            )
            publication.identifier = recommended_paper.get("externalIds", {}).get(
                "DOI", ""
            )
            publication.datePublished = recommended_paper.get(
                "publicationDate", ""
            ) or ""

            for author in recommended_paper.get("authors", []) or []:
                _author = Author()
                _author.additionalType = "Person"
                _author.name = author.get("name", "")
                publication.author.append(_author)

            open_access_pdf = recommended_paper.get("openAccessPdf") or {}
            if recommended_paper.get("isOpenAccess") and open_access_pdf.get("url"):
                publication.encoding_contentUrl = open_access_pdf.get("url", "")

            _source = thing()
            _source.name = self.SOURCE
            rec_paper_id = recommended_paper.get("paperId", "")
            if rec_paper_id:
                _source.identifier = rec_paper_id
                _source.url = f"https://www.semanticscholar.org/paper/{rec_paper_id}"
            publication.source.append(_source)

            if publication.identifier:
                recommended_publications.append(publication)

        return recommended_publications

    def _fetch_citations_by_doi(self, doi: str) -> Dict[str, Any]:
        """
        Retrieve citations for a paper by DOI (with retries).
        Returns the raw response dict or None on failure.
        """
        base_url = self._get_config(self.SOURCE, "citations-endpoint", "")
        identifier = f"{doi}?fields=citations.title,citations.year,citations.externalIds,citations.authors"
        for attempt in range(MAX_RETRIES):
            response = data_retriever.retrieve_object(
                base_url=base_url,
                identifier=identifier,
                quote=False,
            )
            if isinstance(response, dict):
                return response
            self.log_event(
                type="info",
                message=f"{self.SOURCE} - Retry {attempt + 1}/{MAX_RETRIES} for citations",
            )
            time.sleep(RETRY_DELAY_SECONDS)
        return None

    def get_citations_for_publication(self, doi: str) -> List[Article]:
        """
        Fetch citing publications for a given DOI as Article objects.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article.

        Returns:
            List of Article objects for citing publications.
        """
        citations_list: List[Article] = []

        response = self._fetch_citations_by_doi(doi)
        if not response:
            return citations_list

        citations = response.get("citations", [])
        for citation in citations:
            publication = Article()
            publication.name = remove_html_tags(citation.get("title", ""))
            authors = citation.get("authors", [])
            for author in authors:
                _author = Author()
                _author.additionalType = "Person"
                _author.name = author.get("name", "")
                publication.author.append(_author)

            publication.identifier = citation.get("externalIds", {}).get("DOI", "")
            publication.datePublished = citation.get("year", "")

            _source = thing()
            _source.name = self.SOURCE
            publication.source.append(_source)

            citations_list.append(publication)

        return citations_list


# ---------------------------------------------------------------------------
# Module-level entry points (preserve existing API for main.py integration)
# ---------------------------------------------------------------------------


def get_dois_citations(doi: str, tracking=None) -> List[str]:
    """
    Entrypoint: fetch DOIs of citations for a given DOI.
    """
    return SemanticScholarPublications(tracking).get_dois_citations(doi)


def get_recommendations_for_publication(doi: str, tracking=None, limit: int = 100) -> List[Article]:
    """
    Entrypoint: fetch recommended publications for a given DOI as Article objects.
    """
    return SemanticScholarPublications(tracking).get_recommendations_for_publication(doi, limit=limit)


def get_citations_for_publication(doi: str, tracking=None) -> List[Article]:
    """
    Entrypoint: fetch citing publications for a given DOI as Article objects.
    """
    return SemanticScholarPublications(tracking).get_citations_for_publication(doi)
