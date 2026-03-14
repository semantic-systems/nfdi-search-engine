from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol


@dataclass
class SearchRecord:
    results: Dict[str, Any]          # category: list[object]
    meta: Dict[str, Any]             # displayed counts, totals, etc.
    expires_at: float


class ResultStore(Protocol):
    def put(
        self,
        search_id: str,
        results: Dict[str, Any],
        meta: Dict[str, Any],
        ttl_s: Optional[int] = None,
    ) -> None:
        ...

    def get(self, search_id: str) -> Optional[SearchRecord]:
        ...

    def update_meta(self, search_id: str, patch: Dict[str, Any]) -> bool:
        ...
