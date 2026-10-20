from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from redis import Redis

from nfdi_search_engine.common.models.search_result import SearchResult
from nfdi_search_engine.common.serialization import (
    decode_search_result,
    encode_search_result,
)
from nfdi_search_engine.infra.store.result_store import ResultStore, SearchRecord


class RedisResultStore(ResultStore):
    """
    Result store backed by redis, so every web and worker process sees the same
    search results.

    One search is split over several keys:

    - ``<prefix>:<id>:meta``            envelope with the counters and category names
    - ``<prefix>:<id>:cat:<category>``  a redis list, one encoded SearchResult per entry

    Keeping the categories in lists lets pagination read a single page with LRANGE
    instead of deserializing a result set that can run to several megabytes, and keeps
    update_meta a read-modify-write of the small envelope only.
    """

    def __init__(self, client: Redis, key_prefix: str = "search") -> None:
        self.redis = client
        self.prefix = key_prefix

    def _meta_key(self, search_id: str) -> str:
        return f"{self.prefix}:{search_id}:meta"

    def _category_key(self, search_id: str, category: str) -> str:
        return f"{self.prefix}:{search_id}:cat:{category}"

    def put(
        self,
        search_id: str,
        results: Dict[str, List[SearchResult]],
        meta: Dict[str, Any],
        ttl_s: int,
    ) -> None:
        # the category names are stored alongside the meta because an empty category
        # writes no list key, so get() could not otherwise enumerate them
        envelope = {"categories": list(results.keys()), "meta": meta}

        pipe = self.redis.pipeline()
        pipe.set(self._meta_key(search_id), json.dumps(envelope), ex=ttl_s)
        for category, rows in results.items():
            key = self._category_key(search_id, category)
            pipe.delete(key)
            if rows:
                pipe.rpush(key, *[json.dumps(encode_search_result(r)) for r in rows])
                pipe.expire(key, ttl_s)
        pipe.execute()

    def get(self, search_id: str) -> Optional[SearchRecord]:
        envelope = self._envelope(search_id)
        if envelope is None:
            return None

        results = {
            category: self.get_slice(search_id, category, 0, -1)
            for category in envelope["categories"]
        }
        ttl = self.redis.ttl(self._meta_key(search_id))
        return SearchRecord(
            results=results,
            meta=envelope["meta"],
            expires_at=time.time() + max(ttl, 0),
        )

    def get_meta(self, search_id: str) -> Optional[Dict[str, Any]]:
        envelope = self._envelope(search_id)
        return envelope["meta"] if envelope is not None else None

    def get_slice(self, search_id: str, category: str, start: int, count: int) -> List[Any]:
        if count == 0:
            return []
        # count < 0 means "to the end", which is how get() reads a whole category
        stop = -1 if count < 0 else start + count - 1
        rows = self.redis.lrange(self._category_key(search_id, category), start, stop)
        return [decode_search_result(json.loads(row)) for row in rows]

    def update_meta(self, search_id: str, patch: Dict[str, Any]) -> bool:
        key = self._meta_key(search_id)
        envelope = self._envelope(search_id)
        if envelope is None:
            return False

        envelope["meta"].update(patch)

        # concurrent load-more calls for one search can lose an update here and serve
        # a repeated chunk; they are driven by a single session, so it is not guarded
        written = self.redis.set(
            key, 
            json.dumps(envelope), 
            xx=True, 
            keepttl=True
        )
        return bool(written)

    def _envelope(self, search_id: str) -> Optional[Dict[str, Any]]:
        raw = self.redis.get(self._meta_key(search_id))
        return json.loads(raw) if raw is not None else None
