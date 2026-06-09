from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class FieldContribution:
    source: str
    selected: bool
    value_preview: str = ""


@dataclass(frozen=True)
class FieldProvenance:
    field: str
    strategy: str
    contributions: list[FieldContribution] = field(default_factory=list)


@dataclass
class RankingInfo:
    score: float = 0.0
    text_score: float = 0.0
    feature_score: float = 0.0
    signals: dict[str, float] = field(default_factory=dict)
    profile: str = ""


@dataclass
class SearchResult(Generic[T]):
    category: str
    entity_key: str
    item: T
    sources: list[str] = field(default_factory=list)
    provenance: dict[str, FieldProvenance] = field(default_factory=dict)
    ranking: RankingInfo = field(default_factory=RankingInfo)

    # for debugging
    source_items: list[Any] = field(default_factory=list, repr=False)
