from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationSettings:
    """
    Settings for the recommendation service.

    :param recommendation_sources: Map of {display_name: module_name} for every
        source that exposes a non-empty ``recommendations-endpoint``.
    :param limit: Maximum number of recommendations to request per source.
    :param max_workers: Upper bound on threads used to fetch sources in parallel.
    """
    recommendation_sources: dict
    limit: int = 100
    max_workers: int = 16

    @classmethod
    def from_config(cls, cfg: dict) -> "RecommendationSettings":
        recommendation_sources = {
            name: source["module"]
            for name, source in cfg["DATA_SOURCES"].items()
            if str(source.get("recommendations-endpoint", "")).strip()
            and source.get("module")
        }
        return cls(
            recommendation_sources=recommendation_sources,
            limit=int(cfg.get("RECOMMENDATION_LIMIT", 100)),
            max_workers=int(cfg.get("RECOMMENDATION_MAX_WORKERS", 16)),
        )
