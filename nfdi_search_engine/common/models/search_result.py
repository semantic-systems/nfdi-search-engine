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


@dataclass(frozen=True)
class FieldValueProvenance:
    value: Any
    sources: list[str] = field(default_factory=list)


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
    field_provenance: dict[str, FieldValueProvenance] = field(default_factory=dict)
    ranking: RankingInfo = field(default_factory=RankingInfo)

    # for debugging
    source_items: list[Any] = field(default_factory=list, repr=False)

    def item_dict(self, exclude_none: bool = True) -> dict[str, Any]:
        """
        Serialize the merged item for API output.

        When field_provenance is populated, each covered field is emitted as
        {"value": ..., "sources": [...]}; otherwise fields are returned as-is.
        """
        if hasattr(self.item, "model_dump"):
            base = self.item.model_dump(mode="python", exclude_none=exclude_none)
        else:
            base = dict(vars(self.item))
            if exclude_none:
                base = {
                    key: value
                    for key, value in base.items()
                    if value not in (None, "", [], {})
                }

        if not self.field_provenance:
            return base

        return {
            field_name: (
                {"value": fp.value, "sources": list(fp.sources)}
                if (fp := self.field_provenance.get(field_name))
                else value
            )
            for field_name, value in base.items()
        }


@dataclass
class ProvenanceItemView(Generic[T]):
    """
    Template-facing wrapper around SearchResult.

    Attribute access delegates to the merged domain item so existing templates
    keep working; field-level sources are exposed via field_sources() / filters.
    """

    result: SearchResult[T]

    @property
    def search_result(self) -> SearchResult[T]:
        return self.result

    def __getattr__(self, name: str) -> Any:
        return getattr(self.result.item, name)

    def field_sources(self, field_name: str) -> list[str]:
        fp = self.result.field_provenance.get(field_name)
        return list(fp.sources) if fp else []


def resolve_search_result(obj: Any) -> SearchResult | None:
    if isinstance(obj, ProvenanceItemView):
        return obj.result
    if isinstance(obj, SearchResult):
        return obj
    return None


def field_sources_for(obj: Any, field_name: str) -> list[str]:
    if isinstance(obj, ProvenanceItemView):
        return obj.field_sources(field_name)
    result = resolve_search_result(obj)
    if result is None:
        return []
    fp = result.field_provenance.get(field_name)
    return list(fp.sources) if fp else []


@dataclass(frozen=True)
class ProvenanceDisplayRow:
    field: str
    value: str
    sources: str


def format_provenance_value(value: Any, max_len: int = 120) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return ""

    if isinstance(value, list):
        if not value:
            return ""
        if all(isinstance(item, str) for item in value):
            text = ", ".join(value)
        else:
            return f"{len(value)} items"

    elif isinstance(value, dict):
        text = ", ".join(f"{key}: {val}" for key, val in list(value.items())[:3])
    else:
        text = getattr(value, "name", None) or str(value)

    text = " ".join(str(text).split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def provenance_display_rows(
    result: SearchResult,
    *,
    max_value_len: int = 120,
) -> list[ProvenanceDisplayRow]:
    rows: list[ProvenanceDisplayRow] = []
    for field_name in sorted(result.field_provenance):
        fp = result.field_provenance[field_name]
        if not fp.sources:
            continue
        value = format_provenance_value(fp.value, max_len=max_value_len)
        if not value:
            continue
        rows.append(
            ProvenanceDisplayRow(
                field=field_name,
                value=value,
                sources=", ".join(fp.sources),
            )
        )
    return rows


def unwrap_item(obj: Any) -> Any:
    if isinstance(obj, ProvenanceItemView):
        return obj.result.item
    if isinstance(obj, SearchResult):
        return obj.item
    return obj
