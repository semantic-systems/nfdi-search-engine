from __future__ import annotations

from typing import Any

from nfdi_search_engine.common.models.search_result import RankingInfo, SearchResult
from nfdi_search_engine.services.ranking.adapters import (
    ArticleRankingAdapter,
    AuthorRankingAdapter,
    ProjectRankingAdapter,
    RankingAdapter,
    RankingDocument,
    SchemaObjectRankingAdapter,
)
from nfdi_search_engine.services.ranking.profile import RankingProfile
from nfdi_search_engine.services.ranking.query import Query
from nfdi_search_engine.services.ranking.scorers import FieldWeightedTextScorer, FeatureScorer


class RankingService:
    """
    Service for ranking deduplicated search results.

    This service is responsible for:
    - Converting domain objects into normalized RankingDocument objects
    - Applying category-specific RankingProfile configuration
    - Computing text and feature scores
    - Writing RankingInfo back onto each SearchResult
    - Sorting results by descending score

    Ranking profiles are application configuration, not service defaults. If a category has no
    explicit profile, the optional "__default__" config profile is used.
    """

    def __init__(
        self,
        categories: list[str],
        profile_config: dict[str, dict[str, Any]],
        adapters: list[RankingAdapter] | None = None,
        text_scorer: FieldWeightedTextScorer | None = None,
        feature_scorer: FeatureScorer | None = None,
    ) -> None:
        """
        Initialize the ranking service.

        :param categories: Search categories that may be ranked.
        :type categories: list[str]
        :param profile_config: Ranking profile configuration, usually Config.RANKING_PROFILES.
        :type profile_config: dict[str, dict[str, Any]]
        :param adapters: Optional ranking adapters. Defaults to publication, researcher and generic schema adapters.
        :type adapters: list[RankingAdapter] | None
        :param text_scorer: Optional text scorer implementation.
        :type text_scorer: FieldWeightedTextScorer | None
        :param feature_scorer: Optional feature scorer implementation.
        :type feature_scorer: FeatureScorer | None
        """
        self.profiles = self._profiles(categories, profile_config)
        self.adapters = adapters or [
            ArticleRankingAdapter(),
            AuthorRankingAdapter(),
            ProjectRankingAdapter(),
            *[SchemaObjectRankingAdapter(category) for category in categories],
        ]
        self.text_scorer = text_scorer or FieldWeightedTextScorer()
        self.feature_scorer = feature_scorer or FeatureScorer()

    def rank(
        self,
        query_text: str,
        category: str,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """
        Rank SearchResult objects for one result category.

        Each SearchResult is adapted to a RankingDocument, scored against the query and category
        profile, enriched with RankingInfo, and returned in descending score order. The legacy
        item.rankScore field is also populated while templates and source objects still rely on it.

        :param query_text: User search query.
        :type query_text: str
        :param category: Result category, e.g. "publications" or "researchers".
        :type category: str
        :param results: Deduplicated SearchResult objects.
        :type results: list[SearchResult]
        :return: Ranked SearchResult objects in descending score order.
        :rtype: list[SearchResult]
        """
        query = Query.from_string(query_text)
        profile = self.profiles.get(category, RankingProfile.from_dict(category, {}))

        ranked = []
        for result in results:
            doc = self._to_document(result.item, category)
            text_signals = self.text_scorer.score_details(query, doc, profile)
            feature_signals = self.feature_scorer.score_details(query, doc, profile)

            text_score = sum(text_signals.values())
            feature_score = sum(feature_signals.values())
            total_score = text_score + feature_score

            if hasattr(doc.raw, "rankScore"):
                doc.raw.rankScore = total_score

            result.ranking = RankingInfo(
                score=total_score,
                text_score=text_score,
                feature_score=feature_score,
                signals={**text_signals, **feature_signals},
                profile=profile.category,
            )
            ranked.append(result)

        return sorted(ranked, key=lambda r: r.ranking.score, reverse=True)

    def _profiles(
        self,
        categories: list[str],
        profile_config: dict[str, dict[str, Any]],
    ) -> dict[str, RankingProfile]:
        """
        Build RankingProfile instances for all configured search categories.

        Categories without an explicit profile use the optional "__default__" profile. If neither
        exists, an empty profile is used, which keeps ranking deterministic but score-neutral.
        """
        default_config = profile_config.get("__default__", {})
        return {
            category: RankingProfile.from_dict(
                category,
                profile_config.get(category, default_config),
            )
            for category in categories
        }

    def _to_document(self, item: object, category: str) -> RankingDocument:
        """
        Convert a domain object into the RankingDocument consumed by scorers.

        :raises ValueError: If no adapter can handle the object/category combination.
        """
        for adapter in self.adapters:
            if adapter.category == category and adapter.supports(item):
                return adapter.to_document(item)

        raise ValueError(
            f"No ranking adapter found for category={category!r}, "
            f"item_type={type(item).__name__!r}"
        )
