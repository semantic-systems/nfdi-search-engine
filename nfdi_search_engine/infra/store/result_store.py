from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class SearchRecord:
    results: Dict[str, Any]          # category: list[object]
    meta: Dict[str, Any]             # displayed counts, totals, etc.
    expires_at: float


class ResultStore(Protocol):
    """
    Protocol for a result store containing search records
    """
    def put(
        self,
        search_id: str,
        results: Dict[str, Any],
        meta: Dict[str, Any],
        ttl_s: Optional[int] = None,
    ) -> None:
        ...

    def get(self, search_id: str) -> Optional[SearchRecord]:
        """Read the whole record. Only use it when every category is needed."""
        ...

    def get_meta(self, search_id: str) -> Optional[Dict[str, Any]]:
        """Read just the counters, without touching the results."""
        ...

    def get_slice(
        self,
        search_id: str,
        category: str,
        start: int,
        count: int,
    ) -> List[Any]:
        """Read one page of one category, so pagination does not load the rest."""
        ...

    def update_meta(self, search_id: str, patch: Dict[str, Any]) -> bool:
        ...
