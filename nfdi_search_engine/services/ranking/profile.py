from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RankingProfile:
    """
    Category-specific ranking configuration.

    A profile defines which document fields and features should contribute to ranking and
    how strongly each signal should be weighted. Profiles are loaded from Config.RANKING_PROFILES.
    """

    category: str

    field_weights: dict[str, float]
    numeric_feature_weights: dict[str, float] = field(default_factory=dict)
    boolean_feature_weights: dict[str, float] = field(default_factory=dict)
    exact_field_boosts: dict[str, float] = field(default_factory=dict)

    phrase_boost: float = 2.0
    exact_identifier_boost: float = 50.0

    @classmethod
    def from_dict(cls, category: str, data: dict[str, Any]) -> "RankingProfile":
        """
        Build a RankingProfile from configuration data.

        Missing optional sections default to empty mappings, which makes a profile score-neutral
        for those signal types.

        :param category: Search category this profile belongs to.
        :type category: str
        :param data: Profile configuration dictionary.
        :type data: dict[str, Any]
        :return: Parsed ranking profile.
        :rtype: RankingProfile
        """
        return cls(
            category=category,
            field_weights=dict(data.get("field_weights", {})),
            numeric_feature_weights=dict(data.get("numeric_feature_weights", {})),
            boolean_feature_weights=dict(data.get("boolean_feature_weights", {})),
            exact_field_boosts=dict(data.get("exact_field_boosts", {})),
            phrase_boost=float(data.get("phrase_boost", 2.0)),
            exact_identifier_boost=float(data.get("exact_identifier_boost", 50.0)),
        )
