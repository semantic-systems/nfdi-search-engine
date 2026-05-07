import logging
from typing import Any

from nfdi_search_engine.services.deduplication.normalize import normalize_string

log = logging.getLogger(__name__)


def _source_name(obj: Any) -> str | None:
    """Helper to get the source name of an object"""
    sources = getattr(obj, "source", None)
    source = sources[0] if sources else None
    return getattr(source, "name", None) if source else None


def _preference_index(obj: Any, field: str, mapping_preference: dict) -> float:
    """
    Helper to get the preference index of an object's field value based on its source.
    See MAPPING_PREFERENCE in config.py.
    """
    pref = mapping_preference.get(field, mapping_preference.get("__default__", []))
    if not isinstance(pref, list):
        return float("inf")
    src = _source_name(obj)
    return pref.index(src) if src in pref else float("inf")


class ObjectMerger:
    """
    ObjectMerger can be used to merge a list of result objects into one.
    There are different strategies for merging each field, defined by the mapping_preference dict passed to merge().
    """

    def merge(self, group: list[Any], mapping_preference: dict) -> Any:
        """Merge a list of result objects into one, applying strategies from mapping_preference."""
        if not group:
            log.warning("ObjectMerger.merge() called with an empty list")
            return None

        # pick the most specific class among the group as the target type for merging
        # i.e. if we get ['thing', 'thing', 'Publication', 'thing'], we want to merge into a Publication
        target_cls = type(max(group, key=lambda x: len(type(x).__mro__)))
        merged = target_cls()

        # iterate through all fields of the target class
        for field in type(merged).model_fields:
            # default source to "union" so we always collect all sources
            strategy = mapping_preference.get(field) or ("union" if field == "source" else None)

            # build the merged value for this field based on the strategy
            if strategy == "max":
                val = self._apply_max(group, field)
            elif strategy == "union":
                val = self._apply_union(group, field) or None
            else:
                val = self._apply_preference(group, field, mapping_preference)

            if val not in (None, "", [], {}):
                try:
                    # finally, set the merged value on the merged object
                    setattr(merged, field, val)
                except Exception:
                    log.warning("Could not set field %r on %s during merge, skipping", field, target_cls.__name__)

        return merged

    def _apply_max(self, group: list, field: str) -> str | None:
        """
        Return the largest number for a field across all objects, as a string.

        Used e.g. for citationCount, referenceCount, works_count, cited_by_count.
        """
        best = None
        for obj in group:
            try:
                v = float(getattr(obj, field, None))
                if best is None or v > best:
                    best = v
            except (TypeError, ValueError):
                pass
        if best is None:
            return None
        return str(int(best)) if best.is_integer() else str(best)

    def _apply_union(self, group: list, field: str) -> list:
        """
        Concatenate list fields across all objects, deduplicating by _union_key.

        Used e.g. for affiliation, alternateName, researchAreas, keywords.
        """
        seen, combined = set(), []
        for obj in group:
            for item in (getattr(obj, field, None) or []):
                key = self._union_key(item)
                if key not in seen:
                    seen.add(key)
                    combined.append(item)
        return combined

    def _apply_preference(self, group: list, field: str, mapping_preference: dict) -> Any:
        """
        Pick the first non-empty value in source-preference order.

        I.e. if the mapping_preference for this field is ["sourceA", "sourceB", "sourceC"]
        and sourceA is empty, sourceB is X and sourceC is Y, we pick X.
        """
        for obj in sorted(group, key=lambda o: _preference_index(o, field, mapping_preference)):
            val = getattr(obj, field, None)
            if val not in (None, "", [], {}):
                return val
        return None

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
