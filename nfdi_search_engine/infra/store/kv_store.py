from __future__ import annotations

from typing import Optional, Protocol, TypeVar, Generic

T = TypeVar("T")


class KVStore(Protocol, Generic[T]):
    def put(self, key: str, value: T, ttl_s: Optional[int] = None) -> None: ...
    def get(self, key: str) -> Optional[T]: ...
    def delete(self, key: str) -> bool: ...
