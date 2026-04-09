from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from elasticsearch import Elasticsearch, exceptions


def get_es_client(host: str, username: str | None = None, password: str | None = None) -> Elasticsearch:
    """
    Initializes and returns an Elasticsearch client
    """
    auth = (username, password) if username or password else None
    return Elasticsearch(
        host,
        basic_auth=auth,
        # add timeouts/retries as you like:
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=3,
    )
