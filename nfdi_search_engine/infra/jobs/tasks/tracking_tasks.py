from __future__ import annotations

from elasticsearch import ConnectionError
from flask import current_app

from nfdi_search_engine.infra.jobs.celery_app import celery_app
from nfdi_search_engine.infra.jobs.tracking_processor import TrackingProcessor

# Retry only on ConnectionError: the connection never opened, so nothing was sent and a retry cannot write twice
# timeouts are not safe, because the write may have reached elastic
RETRY = {
    "autoretry_for": (ConnectionError,),
    "retry_backoff": True,
    "retry_jitter": True,
    "max_retries": 1, # the elastic client already retries, so one retry here is enough
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
    # this searches for the rows to patch, so it can miss recent writes that elastic has not made searchable yet
    # running jobs in order does not change that
    _processor().handle_propagate_visitor_id(payload)
