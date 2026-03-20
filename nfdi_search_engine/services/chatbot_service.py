from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from urllib.parse import urljoin
import traceback

import requests

from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.common.models.chatbot_settings import ChatbotSettings
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.infra.jobs.dispatcher import JobDispatcher


@dataclass(frozen=True)
class ChatContext:
    """
    Context object for chatbot operations.

    Carries the user question, the search UUID used to look up the previously
    indexed search results (for retrieval/embeddings), and request metadata for
    tracking/logging.
    """
    question: str
    search_uuid: str
    request_meta: RequestMeta
    user_id: Optional[str] = None


@dataclass(frozen=True)
class ChatResponse:
    """
    Chatbot response payload.

    This is currently implemented to reflect the structure by the nfdi-se-chatbot,
    in the future we might want to stick to a standard format, like the one from openai
    """
    chat_history: List[Dict[str, Any]]
    exception: str
    traceback: str


class ChatbotService:
    """
    Service for chatbot integration.

    This service contains the orchestration logic for:
    - Checking whether embeddings have been generated for a given search UUID
    - Sending a user question to the chatbot backend and returning the response
    - Triggering asynchronous indexing of search results for embeddings generation
    """
    def __init__(
        self,
        settings: ChatbotSettings,
        tracking: TrackingService,
        jobs: JobDispatcher,
        http: Optional[requests.Session] = None
    ):
        """
        Initialize the chatbot service.

        :param settings: Chatbot configuration (server URL, endpoints, timeouts).
        :type settings: ChatbotSettings
        :param tracking: Tracking service used to record chatbot interactions.
        :type tracking: TrackingService
        :param jobs: Job dispatcher used for asynchronous indexing tasks.
        :type jobs: JobDispatcher
        :param http: Optional requests session to reuse connections; a new session is created if omitted.
        :type http: Optional[requests.Session]
        """
        self.settings = settings
        self.tracking = tracking
        self.jobs = jobs
        self.http = http or requests.Session()

    def are_embeddings_generated(self, *, search_uuid: str) -> bool:
        """
        Return whether the chatbot backend has finished generating embeddings for a search UUID.

        When the chatbot is disabled via settings, this returns True so that callers can
        proceed without gating UI behavior on the backend.

        :param search_uuid: Search UUID identifying the indexed search results.
        :type search_uuid: str
        :return: True if embeddings are available (or chatbot is disabled), otherwise False.
        :rtype: bool
        :raises requests.RequestException: For network/HTTP errors in enabled mode.
        """
        if not self.settings.enabled:
            return True

        base_url = urljoin(
            f"{self.settings.server}/",
            self.settings.endpoint_are_embeddings_generated.lstrip('/')
        )
        url = f"{base_url}/{search_uuid}"

        resp = self.http.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=self.settings.timeout_s
        )
        resp.raise_for_status()
        data = resp.json()

        return bool(data.get("file_exists", False))

    def get_answer(self, ctx: ChatContext) -> ChatResponse:
        """
        Query the chatbot backend for an answer given a user question and a search UUID.

        :param ctx: Chat request context (question, search uuid, request meta, user id).
        :type ctx: ChatContext
        :return: ChatResponse containing chat history and error/traceback fields.
        :rtype: ChatResponse
        """
        self.tracking.log_activity_async(
            description=f"User asked the chatbot: {ctx.question}",
            request_meta=ctx.request_meta,
            user_id=ctx.user_id,
        )

        if not self.settings.enabled:
            return ChatResponse(
                exception="",
                traceback="",
                chat_history=[{
                    "input": ctx.question,
                    "output": "I'm deactivated :("
                }]
            )

        url = urljoin(
            f"{self.settings.server}/",
            self.settings.endpoint_chat.lstrip('/')
        )

        payload = {"question": ctx.question, "search_uuid": ctx.search_uuid}

        try:
            # I guess that should be POST in the future
            resp = self.http.request(
                "GET",
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.settings.timeout_s,
            )
            resp_json = resp.json()
            return ChatResponse(
                chat_history=resp_json["chat-history"],
                exception=resp_json["exception"],
                traceback=resp_json["traceback"]
            )
        except Exception as ex:
            return ChatResponse(
                chat_history=[],
                exception=str(ex),
                traceback=traceback.format_exc()
            )

    def index_search_results_async(self, search_id: str) -> None:
        """
        Enqueue an asynchronous task to index search results for chatbot embeddings generation.

        This delegates the heavy lifting to a background worker (job dispatcher) so that
        the main request path remains fast. The worker is expected to look up the stored
        search results by search_id and forward them to the chatbot backend.

        :param search_id: Search id identifying the stored full search results.
        :type search_id: str
        :return: None
        :rtype: None
        """
        if not self.settings.enabled:
            return
        self.jobs.enqueue(
            "chatbot.index_search_results",
            {"search_id": search_id}
        )
