from __future__ import annotations

import json
from urllib.parse import urljoin

import requests

from nfdi_search_engine.common.models.search_result import unwrap
from nfdi_search_engine.common.models.chatbot_settings import ChatbotSettings
from nfdi_search_engine.common.serialization import encode_thing
from nfdi_search_engine.infra.store.result_store import ResultStore


class ChatbotProcessor:
    """
    Provides job handlers for asynchronous chatbot operations
    """

    def __init__(self, result_store: ResultStore, settings: ChatbotSettings, http_timeout_s: int = 30):
        self.store = result_store
        self.settings = settings
        self.timeout = http_timeout_s

    def handle_index_search_results(self, payload: dict) -> None:
        search_id = payload["search_id"]

        rec = self.store.get(search_id)
        if not rec:
            return  # expired or missing

        base_url = urljoin(
            f"{self.settings.server}/",
            self.settings.endpoint_save_docs_with_embeddings.lstrip('/')
        )
        request_url = f"{base_url}/{search_id}"

        # the chatbot indexes the domain objects, not the SearchResult wrapper.
        # drop_empty is off so the payload keeps every key the backend saw before.
        results = {
            category: [
                encode_thing(unwrap(row), drop_empty=False)
                for row in rows
            ]
            for category, rows in rec.results.items()
        }

        results_json = json.dumps(results)
        resp = requests.post(
            request_url,
            json=results_json,
            timeout=self.timeout
        )
        resp.raise_for_status()
