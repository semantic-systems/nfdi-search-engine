from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from urllib.parse import urljoin
import traceback

import requests

from nfdi_search_engine.common.request_meta import RequestMeta
from nfdi_search_engine.common.chatbot_settings import ChatbotSettings
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.infra.jobs.dispatcher import JobDispatcher


@dataclass(frozen=True)
class ChatContext:
    question: str
    search_uuid: str
    request_meta: RequestMeta
    user_id: Optional[str] = None


@dataclass(frozen=True)
class ChatResponse:
    """
    This is currently implemented to reflect the structure by the nfdi-se-chatbot,
    in the future we might want to stick to a standard format, like the one from openai
    """
    chat_history: List[Dict[str, Any]]
    exception: str
    traceback: str


class ChatbotService:
    def __init__(
        self,
        settings: ChatbotSettings,
        activity: TrackingService,
        jobs: JobDispatcher,
        http: Optional[requests.Session] = None
    ):
        self.settings = settings
        self.activity = activity
        self.jobs = jobs
        self.http = http or requests.Session()

    def are_embeddings_generated(self, *, search_uuid: str) -> bool:
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
        self.activity.log_activity_async(
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
        if not self.settings.enabled:
            return
        self.jobs.enqueue(
            "chatbot.index_search_results",
            {"search_id": search_id}
        )
