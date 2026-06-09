import math
from collections import Counter
from datetime import date

from nfdi_search_engine.common.strings import tokenize, flatten_string_value
from nfdi_search_engine.services.ranking.query import Query
from nfdi_search_engine.services.ranking.adapters import RankingDocument
from nfdi_search_engine.services.ranking.profile import RankingProfile


class FieldWeightedTextScorer:
    """
    Scores textual relevance using configured field weights.

    The scorer compares tokenized query terms against each configured text field in a
    RankingDocument. It applies light term-frequency saturation, an optional phrase boost,
    and length normalization so very long text fields do not dominate shorter high-signal
    fields such as title or name.
    """

    def score(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> float:
        """
        Return the total text score for a query/document/profile combination.

        :param query: Parsed search query.
        :type query: Query
        :param doc: Ranking document built by a RankingAdapter.
        :type doc: RankingDocument
        :param profile: Category-specific ranking profile.
        :type profile: RankingProfile
        :return: Sum of all text signal scores.
        :rtype: float
        """
        return sum(self.score_details(query, doc, profile).values())

    def score_details(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        """
        Return individual text score signals.

        Keys are signal names such as "text.title" or "text.abstract"; values are weighted
        score contributions. The detailed map is stored in RankingInfo.signals for later
        debugging, explanation or UI display.

        :return: Mapping of text signal name to weighted score contribution.
        :rtype: dict[str, float]
        """
        if not query.tokens:
            return {}

        scores = {}

        for field_name, weight in profile.field_weights.items():
            value = flatten_string_value(doc.fields.get(field_name))
            if not value:
                continue

            field_text = value.lower()
            field_tokens = tokenize(field_text)

            if not field_tokens:
                continue

            token_counts = Counter(field_tokens)

            # Basic term overlap with light term frequency saturation.
            field_score = 0.0
            for token in query.tokens:
                tf = token_counts.get(token, 0)
                if tf:
                    field_score += 1.0 + math.log(tf)

            # Phrase boost.
            if query.raw and query.raw in field_text:
                field_score *= profile.phrase_boost

            # Normalize a bit so huge text fields do not dominate.
            field_score /= math.sqrt(len(field_tokens))

            weighted_score = weight * field_score
            if weighted_score:
                scores[f"text.{field_name}"] = weighted_score

        return scores


class FeatureScorer:
    """
    Scores non-text ranking features.

    Feature signals include identifier matches, exact configured field matches, numeric
    features such as citation counts or years, and boolean completeness features such as
    "has_identifier".
    """

    def score(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> float:
        """
        Return the total feature score for a query/document/profile combination.

        :param query: Parsed search query.
        :type query: Query
        :param doc: Ranking document built by a RankingAdapter.
        :type doc: RankingDocument
        :param profile: Category-specific ranking profile.
        :type profile: RankingProfile
        :return: Sum of all feature signal scores.
        :rtype: float
        """
        return sum(self.score_details(query, doc, profile).values())

    def score_details(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        """
        Return individual feature score signals.

        Keys are signal names such as "feature.identifier.exact" or
        "feature.citation_count"; values are weighted score contributions.

        :return: Mapping of feature signal name to weighted score contribution.
        :rtype: dict[str, float]
        """
        scores = {}
        scores.update(self._identifier_scores(query, doc, profile))
        scores.update(self._exact_field_scores(query, doc, profile))
        scores.update(self._numeric_feature_scores(doc, profile))
        scores.update(self._boolean_feature_scores(doc, profile))

        return scores

    def _identifier_scores(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        """
        Score exact and partial identifier matches.

        This is used for DOI/ORCID-like identifiers where an exact query match should strongly
        dominate ordinary text overlap.
        """
        identifier = flatten_string_value(doc.fields.get("identifier")).lower()

        if not identifier:
            return {}

        if query.raw == identifier:
            return {"feature.identifier.exact": profile.exact_identifier_boost}

        if query.raw in identifier or identifier in query.raw:
            return {"feature.identifier.partial": profile.exact_identifier_boost * 0.5}

        return {}

    def _exact_field_scores(
        self,
        query: Query,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        if not query.raw:
            return {}

        scores = {}
        for field_name, boost in profile.exact_field_boosts.items():
            values = _as_strings(doc.fields.get(field_name))
            for value in values:
                if value.lower().strip() == query.raw:
                    scores[f"feature.{field_name}.exact"] = boost
                    break
        return scores

    def _numeric_feature_scores(
        self,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        """
        Score configured numeric features.

        Count-like features are log-scaled. The "year" feature is converted into a recency
        score so recent items receive a mild boost without overwhelming relevance.
        """
        scores = {}

        for name, weight in profile.numeric_feature_weights.items():
            value = doc.numeric_features.get(name)

            if value is None:
                continue

            # Log-scale count-like features.
            if name.endswith("_count") or name in {"citation_count", "works_count"}:
                value = math.log1p(max(value, 0.0))

            # Very simple year freshness feature.
            if name == "year":
                value = self._year_score(value)

            weighted_score = weight * value
            if weighted_score:
                scores[f"feature.{name}"] = weighted_score

        return scores

    def _boolean_feature_scores(
        self,
        doc: RankingDocument,
        profile: RankingProfile,
    ) -> dict[str, float]:
        scores = {}

        for name, weight in profile.boolean_feature_weights.items():
            if doc.boolean_features.get(name):
                scores[f"feature.{name}"] = weight

        return scores

    def _year_score(self, year: float) -> float:
        """
        Convert a publication/start year into a bounded recency score.
        """
        if not year:
            return 0.0

        # Mild recency boost, not dominance.
        current_year = date.today().year
        age = max(0.0, current_year - year)

        return 1.0 / (1.0 + age)


def _as_strings(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]
