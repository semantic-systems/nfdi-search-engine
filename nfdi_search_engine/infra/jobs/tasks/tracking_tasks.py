from __future__ import annotations

from elasticsearch import ConnectionError, ConnectionTimeout
from flask import current_app

from nfdi_search_engine.infra.jobs.celery_app import celery_app
from nfdi_search_engine.infra.jobs.tracking_processor import TrackingProcessor

# Retry only on connection errors, where the request never reached Elasticsearch.
# handle_upsert_user_agent reads before it writes, so retrying a call that did
# reach the cluster could insert a duplicate.
RETRY = {
    "autoretry_for": (ConnectionError, ConnectionTimeout),
    "retry_backoff": True,
    "retry_jitter": True,
    "max_retries": 3,
}


def _processor() -> TrackingProcessor:
    return current_app.extensions["processors"]["tracking"]


@celery_app.task(name="tracking.activity.write", **RETRY)
def write_activity(doc: dict) -> None:
    _processor().handle_write_activity(doc)


@celery_app.task(name="tracking.search_term.write", **RETRY)
def write_search_term(doc: dict) -> None:
    _processor().handle_write_search_term(doc)


@celery_app.task(name="tracking.event.write", **RETRY)
def write_event(doc: dict) -> None:
    _processor().handle_write_event(doc)


@celery_app.task(name="tracking.user_agent.upsert", **RETRY)
def upsert_user_agent(doc: dict) -> None:
    _processor().handle_upsert_user_agent(doc)


@celery_app.task(name="tracking.visitor_id.propagate", **RETRY)
def propagate_visitor_id(payload: dict) -> None:
    _processor().handle_propagate_visitor_id(payload)
