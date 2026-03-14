from __future__ import annotations

import importlib
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from nfdi_search_engine.common.models.objects import Article
from nfdi_search_engine.common.models.details_settings import DetailsSettings
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.common.merge import merge_objects


class PublicationDetailsService:
    """
    Service for all publication-details operations.

    This service contains the orchestration logic for:
    - DOI reference/citation list retrieval
    - DOI -> metadata resolution for batches
    - Publication details page harvesting across sources
    - Publication merging
    - Publication citations/recommendations partial lists
    - External DOI citation string formatting
    """

    def __init__(
        self,
        settings: DetailsSettings,
        tracking: TrackingService,
        http: Optional[requests.Session] = None,
    ):
        self.settings = settings
        self.tracking = tracking
        self.http = http or requests.Session()

        # we can think about moving this to the config
        self.references_sources = {
            "CROSSREF - Publications": "crossref_publications",
            "OpenCitations": "opencitations",
        }
        self.citation_sources = {
            "SEMANTIC SCHOLAR - Publications": "semanticscholar_publications",
            "OpenCitations": "opencitations",
        }
        self.metadata_sources = {
            "OpenCitations": "opencitations",
        }
        self.recommendation_sources = {
            "SEMANTIC SCHOLAR - Publications": "semanticscholar_publications",
        }

    def get_reference_dois(self, doi: str) -> List[str]:
        """
        Return a unique, normalized list of reference DOIs for a DOI.
        Uses the .get_dois_references() method from source modules.

        :param doi: The DOI to query
        :type doi: str
        :return: Sorted list of unique lowercase DOIs
        :rtype: List[str]
        """
        found: Set[str] = set()
        doi = doi.lower()

        for source, module_name in self.references_sources.items():
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                dois = mod.get_dois_references(
                    source=source, doi=doi, tracking=self.tracking) or []
                found.update(d.lower() for d in dois if d)
            except Exception as e:
                self.tracking.log_event_async(
                    log_type="error",
                    filename=f"sources/{module_name}.py",
                    args=[source, doi],
                    method=f"get_dois_references",
                    message=traceback.format_exception_only(e),
                    traceback=traceback.format_exception(e),
                )
                continue

        return sorted(found)

    def get_citation_dois(self, doi: str) -> List[str]:
        """
        Return a unique, normalized list of citing DOIs for a DOI.
        Uses the .get_dois_citations() method from source modules.

        :param doi: The DOI to query
        :type doi: str
        :return: Sorted list of unique lowercase DOIs
        :rtype: List[str]
        """
        found: Set[str] = set()
        doi = doi.lower()

        for source, module_name in self.citation_sources.items():
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                dois = mod.get_dois_citations(
                    source=source, doi=doi, tracking=self.tracking) or []
                found.update(d.lower() for d in dois if d)
            except Exception as e:
                self.tracking.log_event_async(
                    log_type="error",
                    filename=f"sources/{module_name}.py",
                    args=[source, doi],
                    method=f"get_dois_citations",
                    message=traceback.format_exception_only(e),
                    traceback=traceback.format_exception(e),
                )
                continue

        return sorted(found)

    def get_metadata_for_dois(self, dois: List[str]) -> List[dict]:
        """
        Resolve DOI metadata for a list of DOIs.
        Uses .get_batch_articles() method from source modules.

        :param dois: List of DOIs
        :type dois: List[str]
        :return: JSON-serializable list of article payloads
        :rtype: List[dict]
        """
        # normalize input
        dois = [d.strip().lower() for d in (dois or []) if d and d.strip()]
        if not dois:
            return []

        collected: Dict[str, Any] = {}

        for module_name in self.metadata_sources.values():
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                articles = mod.get_batch_articles(
                    dois=dois, tracking=self.tracking) or []
            except Exception as e:
                self.tracking.log_event_async(
                    log_type="error",
                    filename=f"sources/{module_name}.py",
                    args=[dois],
                    method=f"get_batch_articles",
                    message=traceback.format_exception_only(e),
                    traceback=traceback.format_exception(e),
                )
                continue

            # existing collected keys for dedup
            titles = {
                a.name.lower() for a in collected.values()
                if getattr(a, "name", None)
            }
            dois_seen = {
                a.identifier.lower() for a in collected.values()
                if getattr(a, "identifier", None)
            }

            for art in articles:
                title = (getattr(art, "name", "") or "").lower()
                art_doi = (getattr(art, "identifier", "") or "").lower()
                if title and title in titles:
                    continue
                if art_doi and art_doi in dois_seen:
                    continue
                if art_doi:
                    collected[art_doi] = art

        for d in dois:
            if d not in collected:
                collected[d] = Article(identifier=d, partiallyLoaded=True)

        payload = [a.model_dump(mode="python", exclude_none=True)
                   for a in collected.values()]

        return payload

    def get_publications_for_details_page(
        self,
        *,
        doi: str,
        excluded_sources: Set[str],
    ) -> Tuple[List[Article], List[str]]:
        """
        Harvest publication records across all enabled data sources for a given DOI.
        Uses the .get_publication() method from source modules. 

        :param doi: DOI identifier to query.
        :type doi: str
        :param excluded_sources: Sources to ignore
        :type excluded_sources: Set[str]
        :return: publication article objects, source names that raised an exception
        :rtype: Tuple[List[Article], List[str]]
        """
        doi = doi.lower()

        sources: List[str] = []
        for src in self.settings.data_sources:
            cfg = self.settings.data_sources[src]
            if str(cfg.get("get-publication-endpoint", "")).strip() and src not in excluded_sources:
                sources.append(src)

        def get_publication(source: str, module_name: str, doi_: str) -> tuple[Optional[List[Any]], Optional[Exception]]:
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                partial: List[Any] = []
                mod.get_publication(
                    source, doi_, source, partial, self.tracking
                )
                return partial, None
            except Exception as e:
                return None, e

        publications: List[Article] = []
        failed: List[str] = []

        from concurrent.futures import ThreadPoolExecutor, as_completed

        max_workers = min(self.settings.max_workers, len(sources) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(get_publication, src, self.settings.data_sources[src]["module"], doi): src
                for src in sources
            }
            for fut in as_completed(futures):
                src = futures[fut]
                partial, err = fut.result()
                if err:
                    failed.append(src)
                    module_name = self.settings.data_sources[src]["module"]
                    self.tracking.log_event_async(
                        log_type="error",
                        filename=f"sources/{module_name}.py",
                        args=[src, module_name, doi],
                        method=f"get_publication",
                        message=traceback.format_exception_only(err),
                        traceback=traceback.format_exception(err),
                    )
                    continue

                publications.extend(partial or [])

        return publications, failed

    def merge_publications(self, publications: List[Any]) -> Any:
        """
        Merge multiple publication objects into a single publication representation.

        :param publications: List of publication-like objects
        :type publications: List[Any]
        :return: Single object with merged fields
        :rtype: Any
        """
        if not publications:
            return None
        if len(publications) == 1:
            return publications[0]

        return merge_objects(publications, self.settings.mapping_preference["publications"])

    def get_citations_for_publication(self, doi: str) -> List[Article]:
        """
        Fetch citing publication objects for a DOI.
        Uses the .get_citations_for_publication() method from source modules.

        :param doi: DOI to fetch citations for
        :type doi: str
        :return: List of citing articles
        :rtype: List[Article]
        """
        doi = doi.lower()
        publications: List[Any] = []

        for source, module_name in self.citation_sources.items():
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                found = mod.get_citations_for_publication(
                    source=source, doi=doi, tracking=self.tracking
                ) or []
            except Exception as e:
                self.tracking.log_event_async(
                    log_type="error",
                    filename=f"sources/{module_name}.py",
                    args=[source, doi],
                    method=f"get_citations_for_publication",
                    message=traceback.format_exception_only(e),
                    traceback=traceback.format_exception(e),
                )
                continue

            doi_list = {getattr(pub, "identifier", "") for pub in publications}
            name_list = {
                (getattr(pub, "name", "") or "").lower()
                for pub in publications
            }

            for pub in found:
                if getattr(pub, "identifier", "") not in doi_list and (getattr(pub, "name", "") or "").lower() not in name_list:
                    publications.append(pub)

        return publications

    def get_recommendations_for_publication(self, doi: str) -> List[Article]:
        """
        Fetch recommended publications for a DOI from semantic scholar
        Uses the .get_recommendations_for_publication() method from source modules.

        :param doi: DOI to fetch recommendations for
        :type doi: str
        :return: List of recommended Articles
        :rtype: List[Article]
        """
        doi = doi.lower()
        publications: List[Article] = []

        for source, module_name in self.citation_sources.items():
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                found = mod.get_recommendations_for_publication(
                    source=source, doi=doi, tracking=self.tracking
                ) or []
            except Exception as e:
                self.tracking.log_event_async(
                    log_type="error",
                    filename=f"sources/{module_name}.py",
                    args=[source, doi],
                    method=f"get_recommendations_for_publication",
                    message=traceback.format_exception_only(e),
                    traceback=traceback.format_exception(e),
                )
                continue
            publications.extend(found)

        return publications

    def format_citation(self, doi: str, style: str = "ieee") -> dict:
        """
        Format a DOI citation string using citation.doi.org.

        :param doi: DOI whose citation to format
        :type doi: str
        :param style: Citation style (default: ieee)
        :type style: str
        :return: dict with keys: "doi", "style", "citation"
        :rtype: dict
        """
        doi = (doi or "").strip().lower()
        style = (style or "ieee").strip()

        r = self.http.get(
            "https://citation.doi.org/format",
            params={"doi": doi, "style": style, "lang": "en-US"},
            headers={"Accept": "text/plain; charset=utf-8"},
            timeout=self.settings.formatting_timeout,
        )
        r.raise_for_status()

        return {"doi": doi, "style": style, "citation": r.text.strip()}
