from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from nfdi_search_engine.services.deduplication.normalize import normalize_doi


@dataclass(frozen=True)
class ResourcePolicy:
    """
    Deduplicate resources (datasets, software) by DOI.

    Two resources are merged if their normalized DOIs match.
    No secondary pass.
    """

    category: str = "resources"

    def primary_keys(self, obj: Any) -> Iterable[str]:
        key = normalize_doi(getattr(obj, "identifier", ""))
        if key:
            yield key

    def secondary_keys(self, obj: Any) -> Iterable[str]:
        return []

    def should_merge_secondary_group(self, group: list[Any]) -> bool:
        return False
