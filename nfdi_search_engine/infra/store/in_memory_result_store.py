from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from nfdi_search_engine.infra.store.result_store import SearchRecord, ResultStore


class InMemoryTTLResultStore(ResultStore):
    """
    In-process result store with TTL
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, SearchRecord] = {}

    def put(self, search_id: str, results: Dict[str, Any], meta: Dict[str, Any], ttl_s: int) -> None:
        now = time.time()
        rec = SearchRecord(results=results, meta=meta, expires_at=now + ttl_s)
        with self._lock:
            self._data[search_id] = rec

    def get(self, search_id: str) -> Optional[SearchRecord]:
        now = time.time()
        with self._lock:
            rec = self._data.get(search_id)
            if rec is None:
                return None
            if rec.expires_at <= now:
                self._data.pop(search_id, None)
                return None
            return rec

    def update_meta(self, search_id: str, patch: Dict[str, Any]) -> bool:
        with self._lock:
            rec = self._data.get(search_id)
            if rec is None:
                return False
            rec.meta.update(patch)
            return True
