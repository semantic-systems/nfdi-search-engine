from __future__ import annotations

from enum import Enum

from elasticsearch import Elasticsearch, exceptions


class ESIndex(Enum):
    user_activity_log = 1
    user_agent_log = 2
    users = 3
    event_logs = 4
    search_term_log = 5


def ensure_indices(es: Elasticsearch) -> None:
    """
    Create indices if missing
    """
    for idx in ESIndex:
        try:
            es.indices.create(index=idx.name)
        except exceptions.RequestError as ex:
            # "resource_already_exists_exception" is normal
            if getattr(ex, "error", None) == "resource_already_exists_exception":
                continue
            raise
