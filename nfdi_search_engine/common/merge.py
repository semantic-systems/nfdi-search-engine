import logging
import re
from typing import Any

log = logging.getLogger(__name__)


def _normalize_string(s: str) -> str:
    """Normalize a string for comparison"""
    if not s:
        return ""
    
    # replace punctuation (including dashes and commas) with spaces and collapse multiple spaces into one
    re_punctuation = re.compile(r"[–—\-,\.]+")
    s = re_punctuation.sub(" ", s.strip().lower())

    return " ".join(s.split())


def _union_key(item: Any) -> str:
    """Dedup key for a list item. First try name, then identifier, then the whole item as a string.

    Name-first because nested objects (e.g. affiliations) often carry
    source-specific identifiers that differ across sources.

    I.e. if there are two affiliations "University College London" and "University College, London" they will most likely have different identifiers
    from the different sources, but we still want to deduplicate them.
    """
    # 1. dedup by name
    name = getattr(item, "name", None)
    if name:
        return _normalize_string(name)
    
    # 2. dedup by identifier
    identifier = getattr(item, "identifier", None)
    if identifier:
        return _normalize_string(str(identifier))
    
    # 3. dedup by the whole item as a string (fallback)
    return _normalize_string(str(item))


def _source_name(obj: Any) -> str | None:
    """Get the source name for an object"""
    sources = getattr(obj, "source", None)
    source = sources[0] if sources else None
    return getattr(source, "name", None) if source else None


def _preference_index(obj: Any, field: str, mapping_preference: dict) -> float:
    """Get the preference index of an object for a given field, based on MAPPING_PREFERENCE (see config.py)."""
    pref = mapping_preference.get(field, mapping_preference.get("__default__", []))
    if not isinstance(pref, list):
        return float("inf")
    src = _source_name(obj)
    return pref.index(src) if src in pref else float("inf")


def _apply_max(object_list: list, field: str) -> str | None:
    """
    Return the largest number for a field across all objects, as a string.
    Used for example to find the largest citation number over multiple researcher objects.
    """
    best = None
    # try to convert each value to a number
    # keep track of the largest one
    for obj in object_list:
        try:
            v = float(getattr(obj, field, None))
            if best is None or v > best:
                best = v
        except (TypeError, ValueError):
            pass
    if best is None:
        return None
    return str(int(best)) if best.is_integer() else str(best)


def _apply_union(object_list: list, field: str) -> list:
    """
    Concatenate list fields across all objects, deduplicating by _union_key.
    This is used for example to combine affiliation lists across multiple researcher objects.
    """
    seen, combined = set(), []
    for obj in object_list:
        for item in (getattr(obj, field, None) or []):
            key = _union_key(item)
            if key not in seen:
                seen.add(key)
                combined.append(item)
    return combined


def _apply_preference(object_list: list, field: str, mapping_preference: dict) -> Any:
    """Pick the first non-empty value in source-preference order. See MAPPING_PREFERENCE in config.py."""
    for obj in sorted(object_list, key=lambda o: _preference_index(o, field, mapping_preference)):
        val = getattr(obj, field, None)
        if val not in (None, "", [], {}):
            return val
    return None


def merge_objects(object_list: list, mapping_preference: dict):
    """
    Merge a list of result objects into one. This applies the configured strategies from MAPPING_PREFERENCE (see config.py) for each field.
    Field values can be: "max", "union", or a list of sources (e.g., ["source1", "source2"], where source1 has higher preference than source2).
    """
    if not object_list:
        log.warning("merge_objects called with an empty list")
        return None

    target_cls = type(max(object_list, key=lambda x: len(type(x).__mro__)))
    merged = target_cls()

    for field in type(merged).model_fields:
        # default source to "union" so we always collect all sources
        strategy = mapping_preference.get(field) or ("union" if field == "source" else None)

        # apply the configured strategy for this field across all objects in the list
        if strategy == "max":
            val = _apply_max(object_list, field)
        elif strategy == "union":
            val = _apply_union(object_list, field) or None
        else:
            val = _apply_preference(object_list, field, mapping_preference)

        if val not in (None, "", [], {}):
            try:
                setattr(merged, field, val)
            except Exception:
                log.warning("Could not set field %r on %s during merge, skipping", field, target_cls.__name__)

    return merged
