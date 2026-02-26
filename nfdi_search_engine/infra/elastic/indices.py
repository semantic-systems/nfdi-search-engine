from __future__ import annotations

from enum import Enum

from elasticsearch import Elasticsearch, exceptions


class ESIndex(Enum):
    USER_ACTIVITY_LOG = 1
    USER_AGENT_LOG = 2
    USERS = 3
    EVENT_LOGS = 4
    SEARCH_TERM_LOG = 5


def ensure_indices(es: Elasticsearch) -> None:
    """
    Create indices if missing
    """
    for idx in ESIndex:
        try:
            es.indices.create(index=idx.value)
        except exceptions.RequestError as ex:
            # "resource_already_exists_exception" is normal
            if getattr(ex, "error", None) == "resource_already_exists_exception":
                continue
            raise
