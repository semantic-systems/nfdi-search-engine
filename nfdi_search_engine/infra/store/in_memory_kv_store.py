from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class _KVRecord(Generic[T]):
    value: T
    expires_at: float


class InMemoryTTLKVStore(Generic[T]):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._data: Dict[str, _KVRecord[T]] = {}

    def put(self, key: str, value: T, ttl_s: Optional[int] = None) -> None:
        ttl = ttl_s if ttl_s is not None else 3600
        rec = _KVRecord(value=value, expires_at=time.time() + ttl)
        with self._lock:
            self._data[key] = rec

    def get(self, key: str) -> Optional[T]:
        now = time.time()
        with self._lock:
            rec = self._data.get(key)
            if rec is None:
                return None
            if rec.expires_at <= now:
                self._data.pop(key, None)
                return None
            return rec.value

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None
