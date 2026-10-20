from __future__ import annotations

import importlib
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import zip_longest
from typing import List, Optional, Tuple

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from nfdi_search_engine.common.models.objects import Article
from nfdi_search_engine.common.models.recommendation_settings import RecommendationSettings
from nfdi_search_engine.infra.observability.context import with_parent_context
from nfdi_search_engine.infra.observability.decorators import traced, tracer
from nfdi_search_engine.services.tracking_service import TrackingService

# re-export so callers can import the service and its settings from one module
# (parity with how DetailsSettings is imported alongside PublicationDetailsService)
__all__ = ["RecommendationService", "RecommendationSettings"]


class RecommendationService:
    """
    Service for publication recommendation retrieval.

    Harvests recommended publications for a DOI across all configured
    recommendation sources (currently Semantic Scholar and OpenAlex). Each
    source module exposes a module-level ``get_recommendations_for_publication``
    entrypoint that returns a list of :class:`Article` objects.
    """

    def __init__(self, settings: RecommendationSettings, tracking: TrackingService):
        self.settings = settings
        self.tracking = tracking

    @traced(
        "recommendation_service.get_recommendations_for_publication",
        attrs=lambda self, doi: {
            "recommendation.doi": doi,
            "recommendation.source_count": len(self.settings.recommendation_sources),
            "recommendation.limit": self.settings.limit,
        },
    )
    def get_recommendations_for_publication(self, doi: str) -> List[Article]:
        """
        Fetch recommended publications for a DOI across recommendation sources.

        Sources are harvested in parallel (see :meth:`_harvest`) and then merged
        into a single ordered list (see :meth:`_merge`). The parent span records
        the merged/deduplicated totals.

        :param doi: DOI to fetch recommendations for
        :type doi: str
        :return: List of recommended Articles (deduplicated by DOI and title)
        :rtype: List[Article]
        """
        doi = (doi or "").lower()

        per_source = self._harvest(doi)
        recommendations = self._merge(per_source)

        fetched_count = sum(len(group) for group in per_source)
        span = trace.get_current_span()
        span.set_attribute("recommendation.contributing_source_count", len(per_source))
        span.set_attribute("recommendation.fetched_count", fetched_count)
        span.set_attribute("recommendation.result_count", len(recommendations))
        span.set_attribute(
            "recommendation.deduplicated_count", fetched_count - len(recommendations)
        )

        return recommendations

    @traced(
        "recommendation_service._harvest",
        attrs=lambda self, doi: {
            "recommendation.doi": doi,
            "recommendation.source_count": len(self.settings.recommendation_sources),
        },
    )
    def _harvest(self, doi: str) -> List[List[Article]]:
        """
        Fetch recommendations from every configured source in parallel.

        Each source runs in its own thread and child span (carrying the source
        name and result count), mirroring ``search_service._harvest``. Results are
        collected by source and returned in configuration order - independent of
        thread completion order - so the downstream merge stays deterministic.

        :param doi: DOI to fetch recommendations for
        :type doi: str
        :return: One list of recommendations per contributing source, in config order
        :rtype: List[List[Article]]
        """
        sources = self.settings.recommendation_sources

        def fetch_source(source: str, module_name: str) -> Tuple[Optional[List[Article]], Optional[Exception]]:
            with tracer.start_as_current_span(
                "recommendation_service.fetch_source"
            ) as span:
                span.set_attribute("recommendation.source", source)
                span.set_attribute("recommendation.module", module_name)
                try:
                    mod = importlib.import_module(f"sources.{module_name}")
                    found = mod.get_recommendations_for_publication(
                        doi=doi, tracking=self.tracking, limit=self.settings.limit
                    ) or []
                    span.set_attribute("recommendation.source_result_count", len(found))
                    return found, None
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    return None, e

        results_by_source: dict[str, List[Article]] = {}
        max_workers = min(self.settings.max_workers, len(sources) or 1)
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            # propagate the current trace context so per-source spans stay nested
            fetch_with_ctx = with_parent_context(fetch_source)
            futures = {
                ex.submit(fetch_with_ctx, source, module_name): source
                for source, module_name in sources.items()
            }
            for fut in as_completed(futures):
                source = futures[fut]
                found, err = fut.result()
                if err is not None:
                    self.tracking.log_event_async(
                        log_type="error",
                        filename=f"sources/{sources[source]}.py",
                        args=[source, doi],
                        method="get_recommendations_for_publication",
                        message=traceback.format_exception_only(err),
                        traceback=traceback.format_exception(err),
                    )
                    continue
                if found:
                    results_by_source[source] = found

        # rebuild in configuration order (not completion order) so the merge is deterministic
        return [results_by_source[s] for s in sources if s in results_by_source]

    def _merge(self, per_source: List[List[Article]]) -> List[Article]:
        """
        Merge per-source recommendation lists into a single ordered list.

        This is the one place result ordering is decided. Today it is a
        round-robin interleave (1st of each source, then 2nd of each, ...) so
        every source is represented near the top, with dedup by DOI and title -
        the fairest merge available without a shared relevance score. When a
        ranking engine is introduced, replace the interleave with a score-based
        sort over the deduplicated set; the dedup below stays as-is.

        :param per_source: One list of recommendations per source, in config order
        :type per_source: List[List[Article]]
        :return: Single deduplicated, ordered list of recommendations
        :rtype: List[Article]
        """
        recommendations: List[Article] = []
        seen_dois: set[str] = set()
        seen_names: set[str] = set()
        for rank in zip_longest(*per_source):
            for pub in rank:
                if pub is None:
                    continue
                pub_doi = (getattr(pub, "identifier", "") or "").lower()
                pub_name = (getattr(pub, "name", "") or "").lower()
                if pub_doi and pub_doi in seen_dois:
                    continue
                if pub_name and pub_name in seen_names:
                    continue
                if pub_doi:
                    seen_dois.add(pub_doi)
                if pub_name:
                    seen_names.add(pub_name)
                recommendations.append(pub)
        return recommendations
