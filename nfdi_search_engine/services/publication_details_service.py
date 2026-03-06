from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from objects import Article
from nfdi_search_engine.common.details_settings import DetailsSettings
from nfdi_search_engine.util.merge import merge_objects


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
        http: Optional[requests.Session] = None,
    ):
        self.settings = settings
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
            mod = importlib.import_module(f"sources.{module_name}")
            dois = mod.get_dois_references(source=source, doi=doi) or []
            found.update(d.lower() for d in dois if d)

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
            mod = importlib.import_module(f"sources.{module_name}")
            dois = mod.get_dois_citations(source=source, doi=doi) or []
            found.update(d.lower() for d in dois if d)

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
            mod = importlib.import_module(f"sources.{module_name}")
            articles = mod.get_batch_articles(dois=dois) or []

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

        def get_publication(source: str, module_name: str, doi_: str, source_id_: str):
            mod = importlib.import_module(f"sources.{module_name}")
            partial: List[Any] = []
            mod.get_publication(source, doi_, source_id_, partial)
            return partial

        publications: List[Article] = []
        failed: List[str] = []

        from concurrent.futures import ThreadPoolExecutor, as_completed

        max_workers = min(self.settings.max_workers, len(sources) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(get_publication, src, self.settings.data_sources[src]["module"], doi, src): src
                for src in sources
            }
            for fut in as_completed(futures):
                src = futures[fut]
                try:
                    partial = fut.result()
                    publications.extend(partial or [])
                except Exception:
                    failed.append(src)

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
            mod = importlib.import_module(f"sources.{module_name}")
            found = mod.get_citations_for_publication(
                source=source, doi=doi) or []

            doi_list = {getattr(pub, "identifier", "") for pub in publications}
            name_list = {(getattr(pub, "name", "") or "").lower()
                         for pub in publications}

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
        source = "SEMANTIC SCHOLAR - Publications"
        module_name = "semanticscholar_publications"
        mod = importlib.import_module(f"sources.{module_name}")

        return mod.get_recommendations_for_publication(source=source, doi=doi) or []

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
