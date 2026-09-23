from __future__ import annotations

from dataclasses import asdict
from typing import Any

from nfdi_search_engine.common.models.objects import thing
from nfdi_search_engine.common.models.search_result import (
    FieldContribution,
    FieldProvenance,
    RankingInfo,
    SearchResult,
)

# Key carrying the domain class name, so decode can rebuild the right subclass.
TYPE_KEY = "__type__"

# Values dropped by drop_empty. Every field in the objects.py hierarchy defaults to
# one of these (or to 0 / False, which are deliberately not listed), so dropping
# them is lossless: decode restores the default via model_construct.
_EMPTY: tuple[Any, ...] = (None, "", [], {})

_registry: dict[str, type[thing]] | None = None


def _build_registry() -> dict[str, type[thing]]:
    """Map class name -> class for `thing` and every subclass currently defined."""
    registry: dict[str, type[thing]] = {"thing": thing}
    stack: list[type[thing]] = [thing]
    while stack:
        for subclass in stack.pop().__subclasses__():
            if subclass.__name__ not in registry:
                registry[subclass.__name__] = subclass
                stack.append(subclass)
    return registry


def _resolve(type_name: str) -> type[thing]:
    """
    Look up a domain class by name, rebuilding the registry once on a miss in case
    the class was defined after this module was first imported.
    """
    global _registry

    if _registry is None:
        _registry = _build_registry()

    cls = _registry.get(type_name)
    if cls is None:
        _registry = _build_registry()
        cls = _registry.get(type_name)

    if cls is None:
        raise ValueError(f"Unknown domain type in encoded payload: {type_name!r}")

    return cls


def encode_thing(obj: Any, drop_empty: bool = False) -> Any:
    """
    Encode a domain object into JSON-compatible data, tagged with its runtime class.

    We walk the object ourselves instead of using pydantic, because neither of its
    modes works for this hierarchy:

    - ``model_dump()`` serializes by the *declared* field type, so an Author held in
      ``CreativeWork.author: List[Union[Organization, Person]]`` silently comes back
      as a Person, losing works_count, cited_by_count, researchAreas and works.
    - ``model_dump(serialize_as_any=True)`` would fix that, but raises
      "Circular reference detected" on self-referential models, and `thing.source`,
      `CreativeWork.citation` and `Article.reference` are all self-referential.

    Iterating ``type(obj).model_fields`` uses the runtime class, which avoids both.

    :param obj: Domain object, list, or plain value.
    :param drop_empty: Omit fields whose value is None/""/[]/{}. Lossless for the
        current hierarchy and a large size saving, since most fields are unset.
    """
    if isinstance(obj, thing):
        encoded: dict[str, Any] = {TYPE_KEY: type(obj).__name__}
        for name in type(obj).model_fields:
            value = getattr(obj, name, None)
            if drop_empty and value in _EMPTY:
                continue
            encoded[name] = encode_thing(value, drop_empty=drop_empty)
        return encoded

    if isinstance(obj, list):
        return [encode_thing(value, drop_empty=drop_empty) for value in obj]

    if isinstance(obj, dict):
        return {key: encode_thing(value, drop_empty=drop_empty) for key, value in obj.items()}

    return obj


def decode_thing(data: Any) -> Any:
    """
    Rebuild a domain object from :func:`encode_thing` output.

    Uses ``model_construct`` rather than ``model_validate``, which is substantially 
    faster, Missing fields fall back to their declared defaults and unknown fields
    are ignored, so payloads from an adjacent schema version still decode.
    """
    if isinstance(data, dict) and TYPE_KEY in data:
        cls = _resolve(data[TYPE_KEY])
        fields = {
            key: decode_thing(value)
            for key, value in data.items()
            if key != TYPE_KEY
        }
        return cls.model_construct(**fields)

    if isinstance(data, list):
        return [decode_thing(value) for value in data]

    if isinstance(data, dict):
        return {key: decode_thing(value) for key, value in data.items()}

    return data


def encode_search_result(result: SearchResult, drop_empty: bool = True) -> dict[str, Any]:
    """
    Encode a SearchResult into JSON-compatible data.

    ``source_items`` is intentionally not persisted: it holds every pre-merge source
    object for debugging and roughly doubles the payload.
    """
    return {
        "category": result.category,
        "entity_key": result.entity_key,
        "item": encode_thing(result.item, drop_empty=drop_empty),
        "sources": list(result.sources),
        "provenance": {
            name: {
                "field": field_provenance.field,
                "strategy": field_provenance.strategy,
                "contributions": [
                    asdict(contribution)
                    for contribution in field_provenance.contributions
                ],
            }
            for name, field_provenance in result.provenance.items()
        },
        "ranking": asdict(result.ranking),
    }


def decode_search_result(data: dict[str, Any]) -> SearchResult:
    """
    Rebuild a SearchResult from :func:`encode_search_result` output.
    """
    return SearchResult(
        category=data["category"],
        entity_key=data["entity_key"],
        item=decode_thing(data["item"]),
        sources=list(data.get("sources", [])),
        provenance={
            name: FieldProvenance(
                field=field_provenance["field"],
                strategy=field_provenance["strategy"],
                contributions=[
                    FieldContribution(**contribution)
                    for contribution in field_provenance.get("contributions", [])
                ],
            )
            for name, field_provenance in data.get("provenance", {}).items()
        },
        ranking=RankingInfo(**data.get("ranking", {})),
    )
