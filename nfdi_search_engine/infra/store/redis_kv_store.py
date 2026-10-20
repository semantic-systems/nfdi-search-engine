from __future__ import annotations

import json
from typing import Generic, Optional, TypeVar

from redis import Redis

T = TypeVar("T")


class RedisKVStore(Generic[T]):
    """
    Key-Value store backed by redis, so a value written while serving one request is
    visible to every other web and worker process.

    Values must be JSON serializable. Domain objects are encoded by the caller, see
    common/serialization.py.
    """

    def __init__(
        self,
        client: Redis,
        key_prefix: str = "kv",
        default_ttl_s: int = 3600,
    ) -> None:
        self.redis = client
        self.prefix = key_prefix
        self.default_ttl_s = default_ttl_s

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def put(self, key: str, value: T, ttl_s: Optional[int] = None) -> None:
        self.redis.set(
            self._key(key),
            json.dumps(value),
            ex=ttl_s if ttl_s is not None else self.default_ttl_s,
        )

    def get(self, key: str) -> Optional[T]:
        raw = self.redis.get(self._key(key))
        return json.loads(raw) if raw is not None else None

    def delete(self, key: str) -> bool:
        return self.redis.delete(self._key(key)) > 0
