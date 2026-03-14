# sources/semanticscholar_publications.py
"""
Semantic Scholar Publications source module.

Provides DOI-based lookups for citations and recommendations via the Semantic Scholar API.
This module does not implement search-by-term (BaseSource); it is used only for
publication-details citations and recommendations. Integration points: get_dois_citations,
get_citations_for_publication, get_recommendations_for_publication.
"""
import time
from typing import Dict, Any, List

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

    def get_dois_citations(self, source: str, doi: str) -> List[str]:
        """
        Fetch the DOIs of citations for a given DOI.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article to fetch citations for.

        Returns:
            A list of DOIs of the citing articles.
        """
        base_url = self._get_config(source, "citations-endpoint", "")
        identifier = f"{doi}?fields=citations.externalIds"
        response = data_retriever.retrieve_object(
            source=source,
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

    def get_dois_recommendations(self, source: str, doi: str) -> List[str]:
        """
        Fetch the DOIs of recommendations for a given DOI.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article to fetch recommendations for.

        Returns:
            A list of DOIs of the recommended articles.
        """
        base_url = self._get_config(source, "recommendations-endpoint", "")
        identifier = f"{doi}?fields=externalIds"
        response = data_retriever.retrieve_object(
            source=source,
            base_url=base_url,
            identifier=identifier,
            quote=False,
        )

        if not response or "recommendedPapers" not in response:
            return []

        dois_reference = [
            ref.get("externalIds", {}).get("DOI", "")
            for ref in response["recommendedPapers"]
        ]
        return [d for d in dois_reference if d]

    def _fetch_paper_by_doi(self, source: str, doi: str) -> Dict[str, Any]:
        """
        Retrieve Semantic Scholar paper payload by DOI (with retries).
        Returns the raw response dict or None on failure.
        """
        base_url = self._get_config(source, "citations-endpoint", "")
        for attempt in range(MAX_RETRIES):
            response = data_retriever.retrieve_object(
                source=source,
                base_url=base_url,
                identifier=doi,
                quote=False,
            )
            if isinstance(response, dict):
                return response
            self.log_event(
                type="info",
                message=f"{source} - Retry {attempt + 1}/{MAX_RETRIES} for Semantic Scholar paper ID",
            )
            time.sleep(RETRY_DELAY_SECONDS)
        return None

    def _fetch_recommendations_by_paper_id(
        self, source: str, paper_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve recommendations for a paper by its Semantic Scholar paper ID (with retries).
        Returns the raw response dict or None on failure.
        """
        base_url = self._get_config(source, "recommendations-endpoint", "")
        search_term = f"{paper_id}?fields=title,publicationDate,externalIds&limit=10"
        for attempt in range(MAX_RETRIES):
            response = data_retriever.retrieve_data(
                source=source,
                base_url=base_url,
                search_term=search_term,
                failed_sources=[],
            )
            if isinstance(response, dict):
                return response
            self.log_event(
                type="info",
                message=f"{source} - Retry {attempt + 1}/{MAX_RETRIES} for recommendations",
            )
            time.sleep(RETRY_DELAY_SECONDS)
        return None

    def get_recommendations_for_publication(
        self, source: str, doi: str
    ) -> List[Article]:
        """
        Fetch recommended publications for a given DOI as Article objects.

        Resolves the DOI to a Semantic Scholar paper ID, then fetches recommendations.
        Only articles with a non-empty DOI are included.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article.

        Returns:
            List of Article objects for recommended publications.
        """
        recommended_publications: List[Article] = []

        paper_response = self._fetch_paper_by_doi(source, doi)
        if not paper_response:
            return recommended_publications

        paper_id = paper_response.get("paperId", "")
        if not paper_id:
            return recommended_publications

        self.log_event(
            type="info",
            message=f"{source} - Resolved DOI to Semantic Scholar paper_id: {paper_id}",
        )

        rec_response = self._fetch_recommendations_by_paper_id(source, paper_id)
        if not rec_response:
            return recommended_publications

        recommended_papers = rec_response.get("recommendedPapers", [])
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
            )

            if publication.identifier:
                recommended_publications.append(publication)

        return recommended_publications

    def _fetch_citations_by_doi(self, source: str, doi: str) -> Dict[str, Any]:
        """
        Retrieve citations for a paper by DOI (with retries).
        Returns the raw response dict or None on failure.
        """
        base_url = self._get_config(source, "citations-endpoint", "")
        identifier = f"{doi}?fields=citations.title,citations.year,citations.externalIds,citations.authors"
        for attempt in range(MAX_RETRIES):
            response = data_retriever.retrieve_object(
                source=source,
                base_url=base_url,
                identifier=identifier,
                quote=False,
            )
            if isinstance(response, dict):
                return response
            self.log_event(
                type="info",
                message=f"{source} - Retry {attempt + 1}/{MAX_RETRIES} for citations",
            )
            time.sleep(RETRY_DELAY_SECONDS)
        return None

    def get_citations_for_publication(self, source: str, doi: str) -> List[Article]:
        """
        Fetch citing publications for a given DOI as Article objects.

        Args:
            source: Data source name (used for config lookup).
            doi: The DOI of the article.

        Returns:
            List of Article objects for citing publications.
        """
        citations_list: List[Article] = []

        response = self._fetch_citations_by_doi(source, doi)
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
            _source.name = source
            publication.source.append(_source)

            citations_list.append(publication)

        return citations_list


# ---------------------------------------------------------------------------
# Module-level entry points (preserve existing API for main.py integration)
# ---------------------------------------------------------------------------


def get_dois_citations(source: str, doi: str, tracking=None) -> List[str]:
    """
    Entrypoint: fetch DOIs of citations for a given DOI.
    """
    return SemanticScholarPublications(tracking).get_dois_citations(source, doi)


def get_dois_recommendations(source: str, doi: str, tracking=None) -> List[str]:
    """
    Entrypoint: fetch DOIs of recommendations for a given DOI.
    """
    return SemanticScholarPublications(tracking).get_dois_recommendations(source, doi)


def get_recommendations_for_publication(source: str, doi: str, tracking=None) -> List[Article]:
    """
    Entrypoint: fetch recommended publications for a given DOI as Article objects.
    """
    return SemanticScholarPublications(tracking).get_recommendations_for_publication(
        source, doi
    )


def get_citations_for_publication(source: str, doi: str, tracking=None) -> List[Article]:
    """
    Entrypoint: fetch citing publications for a given DOI as Article objects.
    """
    return SemanticScholarPublications(tracking).get_citations_for_publication(source, doi)
