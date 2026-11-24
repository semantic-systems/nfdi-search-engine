from __future__ import annotations

import logging
import time
from enum import Enum

from elasticsearch import Elasticsearch, exceptions

log = logging.getLogger(__name__)


class ESIndex(Enum):
    user_activity_log = 1
    user_agent_log = 2
    users = 3
    event_logs = 4
    search_term_log = 5


def ensure_indices(es: Elasticsearch, attempts: int = 30, delay_s: float = 2.0) -> None:
    """
    Create indices if missing, waiting for elastic to become reachable.

    Elastic is provisioned separately from the application (see compose.infra.yml), so
    it can still be starting when the web, worker and beat containers come up. All
    three call this through create_app(), and without the retry all three crash-loop
    through their restart policy until elastic answers.
    """
    for attempt in range(1, attempts + 1):
        try:
            for idx in ESIndex:
                try:
                    es.indices.create(index=idx.name)
                except exceptions.RequestError as ex:
                    # "resource_already_exists_exception" is normal
                    if getattr(ex, "error", None) == "resource_already_exists_exception":
                        continue
                    raise
            return
        except (exceptions.ConnectionError, exceptions.ConnectionTimeout):
            if attempt == attempts:
                raise
            log.warning(
                "Elastic not reachable yet, retrying (%d/%d)", attempt, attempts
            )
            time.sleep(delay_s)
