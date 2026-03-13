from __future__ import annotations

import importlib
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from rank_bm25 import BM25Plus

from concurrent.futures import ThreadPoolExecutor, as_completed

from nfdi_search_engine.common.models.search_settings import SearchSettings
from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.infra.store.result_store import ResultStore
from nfdi_search_engine.services.chatbot_service import ChatbotService
from nfdi_search_engine.services.tracking_service import TrackingService


CATEGORIES: List[str] = [
    "publications",
    "researchers",
    "resources",
    "organizations",
    "events",
    "projects",
    "others",
]


@dataclass(frozen=True)
class SearchContext:
    search_id: str
    search_term: str
    excluded_sources: Set[str]
    request_meta: RequestMeta
    user_id: Optional[str] = None
    object_type: Optional[str] = None


@dataclass(frozen=True)
class SearchPage:
    search_id: str
    search_term: str
    results: Dict[str, List[Any]]
    displayed_results: Dict[str, int]
    total_results: Dict[str, int]
    failed_sources: List[str]


class SearchService:
    def __init__(
        self,
        settings: SearchSettings,
        chatbot: ChatbotService,
        store: ResultStore,
        tracking: TrackingService,
    ) -> None:
        self.settings = settings
        self.chatbot = chatbot
        self.store = store
        self.tracking = tracking

    def run_search(self, ctx: SearchContext) -> SearchPage:
        self.tracking.log_activity_async(
            description=f"loading search results for {ctx.search_term}",
            request_meta=ctx.request_meta,
            user_id=ctx.user_id,
        )
        self.tracking.log_search_term_async(
            search_term=ctx.search_term,
            request_meta=ctx.request_meta,
            user_id=ctx.user_id,
        )

        active_sources: List[str] = []
        for src in self.settings.data_sources:
            cfg = self.settings.data_sources[src]
            has_endpoint = str(cfg.get("search-endpoint", "")).strip() != ""
            if has_endpoint and src not in ctx.excluded_sources:
                active_sources.append(src)

        results_full, failed_sources = self._harvest(
            active_sources,
            ctx.search_term
        )

        # sort per category
        for k in CATEGORIES:
            # filter empty
            results_full[k] = [r for r in results_full[k] if r is not None]
            results_full[k] = self._sort_search_results(
                ctx.search_term, results_full[k]
            )

        total_results = {k: len(v) for k, v in results_full.items()}
        displayed = {
            k: min(self.settings.first_page_n, total_results[k])
            for k in CATEGORIES
        }

        # store full results + meta in store
        self.store.put(
            search_id=ctx.search_id,
            results=results_full,
            meta={
                "search_term": ctx.search_term,
                "total_results": total_results,
                "displayed": displayed,
            },
            ttl_s=self.settings.results_ttl_s,
        )

        # chatbot indexing async
        self.chatbot.index_search_results_async(ctx.search_id)

        # first page slice
        page_results = {
            k: results_full[k][: self.settings.first_page_n] for k in CATEGORIES
        }

        return SearchPage(
            search_id=ctx.search_id,
            search_term=ctx.search_term,
            results=page_results,
            displayed_results=displayed,
            total_results=total_results,
            failed_sources=failed_sources,
        )

    def load_more(self, ctx: SearchContext) -> List[Any]:
        if ctx.object_type not in CATEGORIES:
            raise KeyError(f"Invalid object_type: {ctx.object_type}")

        rec = self.store.get(ctx.search_id)
        if rec is None:
            raise KeyError("search_id not found or expired")

        results_full: Dict[str, List[Any]] = rec.results
        meta = rec.meta

        total = int(meta["total_results"][ctx.object_type])
        displayed = int(meta["displayed"][ctx.object_type])

        n = self.settings.lazy_load_n
        chunk = results_full[ctx.object_type][displayed: min(
            displayed + n, total)]

        new_displayed = min(displayed + len(chunk), total)
        meta["displayed"][ctx.object_type] = new_displayed
        self.store.update_meta(ctx.search_id, {"displayed": meta["displayed"]})

        self.tracking.log_activity_async(
            description=f"loading more {ctx.object_type}",
            request_meta=ctx.request_meta,
            user_id=ctx.user_id,
        )

        return chunk, new_displayed, total

    def update_search_result_block(self, source: str, source_identifier: str, doi: str) -> Any:
        if source not in self.settings.data_sources:
            raise KeyError(f"Unknown source: {source}")

        module_name = self.settings.data_sources[source].get("module", "")
        if not module_name:
            raise KeyError(f"No module configured for source: {source}")

        try:
            mod = importlib.import_module(f"sources.{module_name}")
            clean_doi = doi.replace("DOI:", "")
            return mod.get_resource(source, source_identifier, clean_doi, tracking=self.tracking)
        except Exception as e:
            self.tracking.log_event_async(
                log_type="error",
                filename=mod.__file__,
                args=[source, source_identifier, clean_doi],
                method="get_resource",
                message=traceback.format_exception_only(e),
                traceback=traceback.format_exception(e),
            )

    def _harvest(self, sources: List[str], search_term: str) -> Tuple[Dict[str, List[Any]], List[str]]:
        results: Dict[str, List[Any]] = {c: [] for c in CATEGORIES}
        failed: List[str] = []

        def search_source(source: str, module_name: str, term: str) -> tuple[Optional[dict], Optional[Exception]]:
            try:
                mod = importlib.import_module(f"sources.{module_name}")
                partial = {c: [] for c in CATEGORIES}
                failed_sources: List[str] = []
                mod.search(
                    source, term, partial, failed_sources, tracking=self.tracking
                )
                if failed_sources:
                    return None, Exception(f"Failed to harvest {source}")
                return partial, None
            except Exception as e:
                return None, e

        max_workers = min(self.settings.max_workers, len(sources) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(search_source, src, self.settings.data_sources[src]["module"], search_term): src
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
                        args=[src, module_name, search_term],
                        method=f"search",
                        message=traceback.format_exception_only(err),
                        traceback=traceback.format_exception(err),
                    )
                    continue

                for k in CATEGORIES:
                    results[k].extend(partial[k])

        return results, failed

    def _sort_search_results(self, search_term, search_results) -> list:
        tokenized_results = [
            str(result).lower().split(" ")
            for result in search_results
        ]
        if len(tokenized_results) > 0:
            bm25 = BM25Plus(tokenized_results)

            tokenized_query = search_term.lower().split(" ")
            doc_scores = bm25.get_scores(tokenized_query)

            for idx, doc_score in enumerate(doc_scores):
                search_results[idx].rankScore = doc_score

        return sorted(search_results, key=lambda x: x.rankScore, reverse=True)
