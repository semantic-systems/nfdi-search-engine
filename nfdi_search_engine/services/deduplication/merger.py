import hashlib
import logging
from typing import Any

from nfdi_search_engine.common.models.search_result import (
    FieldContribution,
    FieldProvenance,
    FieldValueProvenance,
    SearchResult,
)
from nfdi_search_engine.services.deduplication.normalize import normalize_string

log = logging.getLogger(__name__)


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _source_names(obj: Any) -> list[str]:
    sources = getattr(obj, "source", None)
    names = []

    if isinstance(sources, str):
        names.append(sources)
    elif isinstance(sources, list):
        for source in sources:
            if isinstance(source, str):
                names.append(source)
            elif name := getattr(source, "name", ""):
                names.append(name)

    if not names and (original_source := getattr(obj, "originalSource", "")):
        names.append(original_source)

    return list(dict.fromkeys(name for name in names if name))


def _source_name(obj: Any) -> str | None:
    names = _source_names(obj)
    return names[0] if names else None


def _sources_from_contributions(
    group: list[Any],
    field_prov_record: FieldProvenance,
) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for contribution in field_prov_record.contributions:
        for obj in group:
            for name in _source_names(obj):
                if name == contribution.source and name not in seen:
                    seen.add(name)
                    sources.append(name)
    return sources


def _preference_index(obj: Any, field: str, mapping_preference: dict) -> float:
    """
    Helper to get the preference index of an object's field value based on its source.
    See MAPPING_PREFERENCE in config.py.
    """
    pref = mapping_preference.get(
        field,
        mapping_preference.get("__default__", [])
    )
    if not isinstance(pref, list):
        return float("inf")
    src = _source_name(obj)
    return pref.index(src) if src in pref else float("inf")


class ObjectMerger:
    """
    Merge source objects according to MAPPING_PREFERENCE.

    When category is omitted this returns one merged domain object.
    When category is provided it returns a SearchResult with provenance metadata for search-result storage/ranking.
    """

    def __init__(self, enable_provenance: bool = False) -> None:
        self.enable_provenance = enable_provenance

    def merge(
        self,
        group: list[Any],
        mapping_preference: dict,
        category: str | None = None,
        entity_key: str = "",
        enable_provenance: bool | None = None,
    ) -> Any:
        """
        Merge a list of result objects into one.
        Returns a SearchResult if a category if provided, the domain object otherwise.
        Applies strategies from mapping_preference and adds the provenance record.
        """
        use_provenance = (
            self.enable_provenance
            if enable_provenance is None
            else enable_provenance
        )
        source_items = self._source_items(group)
        if not source_items:
            log.warning("ObjectMerger.merge() called with an empty list")
            return None

        # pick the most specific class among the group as the target type for merging
        # i.e. if we get ['thing', 'thing', 'Publication', 'thing'], we want to merge into a Publication
        target_cls = type(max(
            source_items,
            key=lambda x: len(type(x).__mro__)
        ))
        merged = target_cls()
        provenance = {}
        field_level_provenance: dict[str, FieldValueProvenance] = {}

        # iterate through all fields of the target class
        for field in type(merged).model_fields:
            # default source to "union" so we always collect all sources
            strategy = mapping_preference.get(field) or (
                "union" if field == "source" else "preference"
            )

            # build the merged value for this field based on the strategy
            if strategy == "max":
                value, field_prov_record = self._value_max(group, field)
            elif strategy == "union":
                value, field_prov_record = self._value_union(group, field)
            else:
                value, field_prov_record = self._value_preference(
                    group,
                    field,
                    mapping_preference
                )

            if not _is_empty(value):
                try:
                    # finally, set the merged value on the merged object
                    setattr(merged, field, value)
                except Exception:
                    log.warning(
                        "Could not set field %r on %s during merge, skipping", field, target_cls.__name__)

            if field_prov_record.contributions:
                provenance[field] = field_prov_record

            if use_provenance and not _is_empty(value):
                field_level_provenance[field] = FieldValueProvenance(
                    value=value,
                    sources=_sources_from_contributions(group, field_prov_record),
                )

        if category is None:
            return merged

        return SearchResult(
            category=category,
            entity_key=entity_key or self._entity_key(category, merged),
            item=merged,
            sources=self._sources(source_items),
            provenance=provenance,
            field_provenance=field_level_provenance if use_provenance else {},
            source_items=source_items,
        )

    def _contribution(self, obj: Any, field: str, selected: bool) -> FieldContribution:
        return FieldContribution(
            source=_source_name(obj) or type(obj).__name__,
            selected=selected,
            value_preview=self._preview(getattr(obj, field, "")),
        )

    def _value_max(self, group: list[Any], field: str) -> tuple[Any, FieldProvenance]:
        """
        Return the largest number and the provenance record for a field across all objects.

        Used e.g. for citationCount, referenceCount, works_count, cited_by_count.
        """
        candidates = []
        for obj in group:
            try:
                candidates.append((float(getattr(obj, field, None)), obj))
            except (TypeError, ValueError):
                continue

        if not candidates:
            return None, FieldProvenance(field=field, strategy="max")

        best = max(numeric for numeric, _ in candidates)
        winner = next(obj for numeric, obj in candidates if numeric == best)
        value = getattr(winner, field)

        contributions = [
            self._contribution(obj, field, numeric == best)
            for numeric, obj in candidates
        ]
        return value, FieldProvenance(field=field, strategy="max", contributions=contributions)

    def _value_union(self, group: list[Any], field: str) -> tuple[Any, FieldProvenance]:
        """
        Concatenate list fields across all objects, deduplicating by _union_key.

        Used e.g. for affiliation, alternateName, researchAreas, keywords.
        """
        field_lists = {id(obj): self._as_list(
            getattr(obj, field, None)) for obj in group}

        seen: set = set()
        combined: list[Any] = []
        contributing_ids: set = set()  # objects that supplied at least one new item
        for obj in group:
            for item in field_lists[id(obj)]:
                key = self._union_key(item)
                if key not in seen:
                    seen.add(key)
                    combined.append(item)
                    contributing_ids.add(id(obj))

        contributions = [
            self._contribution(obj, field, id(obj) in contributing_ids)
            for obj in group
            if field_lists[id(obj)]
        ]
        return combined, FieldProvenance(field=field, strategy="union", contributions=contributions)

    def _value_preference(
        self, group: list[Any], field: str, mapping_preference: dict
    ) -> tuple[Any, FieldProvenance]:
        """
        Pick the first non-empty value in source-preference order.

        I.e. if the mapping_preference for this field is ["sourceA", "sourceB", "sourceC"]
        and sourceA is empty, sourceB is X and sourceC is Y, we pick X.
        """
        field_values = {id(obj): getattr(obj, field, None) for obj in group}

        selected_obj = None
        for obj in sorted(group, key=lambda o: _preference_index(o, field, mapping_preference)):
            if not _is_empty(field_values[id(obj)]):
                selected_obj = obj
                break

        selected_value = field_values[id(
            selected_obj)] if selected_obj is not None else None
        contributions = [
            self._contribution(obj, field, obj is selected_obj)
            for obj in group
            if not _is_empty(field_values[id(obj)])
        ]
        return selected_value, FieldProvenance(
            field=field, strategy="preference", contributions=contributions
        )

    def _source_items(self, group: list[Any]) -> list[Any]:
        items = []
        for obj in group:
            if isinstance(obj, SearchResult):
                items.extend(obj.source_items or [obj.item])
            else:
                items.append(obj)
        return items

    def _sources(self, group: list[Any]) -> list[str]:
        seen, names = set(), []
        for obj in group:
            for name in _source_names(obj):
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def _entity_key(self, category: str, obj: Any) -> str:
        for field in ("identifier", "url", "name"):
            value = getattr(obj, field, "")
            if value:
                return f"{category}:{normalize_string(str(value))}"

        digest = hashlib.sha1(str(obj).encode(
            "utf-8", errors="ignore")).hexdigest()
        return f"{category}:{digest[:16]}"

    def _as_list(self, value: Any) -> list[Any]:
        if _is_empty(value):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _preview(self, value: Any) -> str:
        if _is_empty(value):
            return ""
        if isinstance(value, list):
            value = ", ".join(self._preview(v) for v in value[:3])
        else:
            value = getattr(value, "name", None) or str(value)
        value = " ".join(str(value).split())
        return value[:160]

    def _union_key(self, item: Any) -> str:
        """
        Dedup key for a list item. Name-first, then identifier, then string repr.

        Name-first because nested objects (e.g. affiliations) often carry
        source-specific identifiers that differ across sources.
        """
        name = getattr(item, "name", None)
        if name:
            return normalize_string(name)
        identifier = getattr(item, "identifier", None)
        if identifier:
            return normalize_string(str(identifier))
        return normalize_string(str(item))
