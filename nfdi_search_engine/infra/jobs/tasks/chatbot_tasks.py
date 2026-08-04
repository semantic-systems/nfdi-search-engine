from __future__ import annotations

from flask import current_app
from requests.exceptions import RequestException

from nfdi_search_engine.infra.jobs.celery_app import celery_app
from nfdi_search_engine.infra.jobs.chatbot_processor import ChatbotProcessor


def _processor() -> ChatbotProcessor:
    return current_app.extensions["processors"]["chatbot"]


@celery_app.task(
    name="chatbot.index_search_results",
    autoretry_for=(RequestException,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def index_search_results(payload: dict) -> None:
    _processor().handle_index_search_results(payload)
