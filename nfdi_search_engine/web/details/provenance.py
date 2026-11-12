"""Turn the merger's field provenance into rows for the provenance modal."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Hashable

from nfdi_search_engine.common.models.search_result import (
    FieldContribution,
    FieldProvenance,
    SearchResult,
)
from nfdi_search_engine.services.deduplication.merger import preview, source_name
from nfdi_search_engine.services.deduplication.normalize import (
    normalize_doi,
    normalize_orcid,
    normalize_string,
)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(text for v in value if (text := _text(v)))
    return " ".join(str(getattr(value, "name", None) or value).split())


def _count(value: Any) -> str:
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return _text(value)


def _text_key(value: Any, strategy: str) -> Hashable:
    if isinstance(value, (list, tuple)):
        keys = [k for v in value if (k := _text_key(v, strategy))]
        return frozenset(keys) if strategy == "union" else tuple(keys)
    return normalize_string(_text(value))


def _count_key(value: Any, strategy: str) -> Hashable:
    return _count(value)


def _date_key(value: Any, strategy: str) -> Hashable:
    return _text(value)[:10]


def _doi_key(value: Any, strategy: str) -> Hashable:
    return normalize_doi(value)


def _orcid_key(value: Any, strategy: str) -> Hashable:
    return normalize_orcid(value)


def _person_list_key(value: Any, strategy: str) -> Hashable:
    # "Lecun, Yann" and "Yann LeCun" are the same person
    return tuple(" ".join(sorted(normalize_string(_text(p)).split())) for p in value or [])


@dataclass(frozen=True)
class ProvenanceField:
    name: str
    label: str
    fmt: Callable[[Any], str] = _text
    # values with equal keys count as the same value
    key: Callable[[Any, str], Hashable] = _text_key


# fields shown in the modal per SearchResult category, in display order
PROVENANCE_FIELDS: dict[str, tuple[ProvenanceField, ...]] = {
    "publications": (
        ProvenanceField("name", "Title"),
        ProvenanceField("author", "Authors", key=_person_list_key),
        ProvenanceField("abstract", "Abstract"),
        ProvenanceField("keywords", "Keywords"),
        ProvenanceField("identifier", "DOI", key=_doi_key),
        ProvenanceField("datePublished", "Publication date", key=_date_key),
        ProvenanceField("publication", "Published in"),
        ProvenanceField("license", "License"),
        ProvenanceField("referenceCount", "References", _count, _count_key),
        ProvenanceField("citationCount", "Citations", _count, _count_key),
    ),
    "researchers": (
        ProvenanceField("name", "Name"),
        ProvenanceField("alternateName", "Other names"),
        ProvenanceField("identifier", "ORCID", key=_orcid_key),
        ProvenanceField("affiliation", "Affiliations"),
        ProvenanceField("researchAreas", "Research areas"),
        ProvenanceField("works_count", "Publications", _count, _count_key),
        ProvenanceField("cited_by_count", "Citations", _count, _count_key),
    ),
}


@dataclass(frozen=True)
class SourceValue:
    source: str
    value: str
    # sources with equivalent values share a group; group 0 holds the merged value's source
    group: int


@dataclass(frozen=True)
class ProvenanceRow:
    label: str
    value: str
    sources: tuple[SourceValue, ...]

    @property
    def conflict(self) -> bool:
        return len({s.group for s in self.sources}) > 1


def _contributed_value(
    field: str,
    contribution: FieldContribution,
    items_by_source: dict[str, list[Any]],
) -> Any:
    """
    The full value behind a contribution. A source can deliver several items,
    so the item is matched by the preview the merger recorded.
    """
    for item in items_by_source.get(contribution.source, []):
        value = getattr(item, field, None)
        if preview(value) == contribution.value_preview:
            return value
    return contribution.value_preview


def _source_values(
    spec: ProvenanceField,
    prov: FieldProvenance,
    items_by_source: dict[str, list[Any]],
) -> tuple[SourceValue, ...]:
    groups: dict[Hashable, int] = {}
    values: list[SourceValue] = []
    seen: set[tuple[str, int]] = set()
    # selected sources first, the rest keep the merger's source preference order
    for contribution in sorted(prov.contributions, key=lambda c: not c.selected):
        raw = _contributed_value(spec.name, contribution, items_by_source)
        group = groups.setdefault(spec.key(raw, prov.strategy), len(groups))
        if (contribution.source, group) in seen:
            continue
        seen.add((contribution.source, group))
        values.append(SourceValue(contribution.source, spec.fmt(raw), group))
    return tuple(sorted(values, key=lambda v: v.group))


def provenance_rows(result: SearchResult) -> list[ProvenanceRow]:
    """
    One row per field of the result's category that has provenance: the merged
    value and every contributing source, grouped by value.
    """
    items_by_source: dict[str, list[Any]] = defaultdict(list)
    for item in result.source_items:
        items_by_source[source_name(item) or type(item).__name__].append(item)

    rows = []
    for spec in PROVENANCE_FIELDS.get(result.category, ()):
        prov = result.provenance.get(spec.name)
        value = spec.fmt(getattr(result.item, spec.name, None))
        if prov is None or not value:
            continue
        rows.append(ProvenanceRow(spec.label, value, _source_values(spec, prov, items_by_source)))
    return rows
