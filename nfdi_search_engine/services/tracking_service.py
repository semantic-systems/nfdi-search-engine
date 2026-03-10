from __future__ import annotations

from datetime import date, datetime, timezone
from dataclasses import asdict
import inspect
import os

from elasticsearch import Elasticsearch

from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.infra.elastic.indices import ESIndex
from nfdi_search_engine.infra.jobs.dispatcher import JobDispatcher
from nfdi_search_engine.common.dates import to_es_range


class TrackingService:
    def __init__(self, es_client: Elasticsearch, jobs: JobDispatcher, es_date_format: str = "%Y-%m-%d"):
        self.es = es_client
        self.jobs = jobs
        self.es_date_format = es_date_format

    def log_activity_async(self, description: str, request_meta: RequestMeta, user_id: str | None = None) -> None:
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "description": description,
            "user_id": user_id,
            **asdict(request_meta),
        }
        self.jobs.enqueue("tracking.activity.write", doc)

    def log_search_term_async(self, search_term: str, request_meta: RequestMeta, user_id: str | None = None) -> None:
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "search_term": search_term,
            "user_id": user_id,
            **asdict(request_meta),
        }
        self.jobs.enqueue("tracking.search_term.write", doc)

    def log_user_agent_async(self, user_agent_doc: dict) -> None:
        """
        user_agent_doc is already parsed/built at the web boundary (or helper),
        and contains session_id/user_email/visitor_id/url/ip/etc.
        """
        payload = {
            "timestamp_created": datetime.now(timezone.utc),
            "timestamp_updated": datetime.now(timezone.utc),
            **user_agent_doc,
        }
        self.jobs.enqueue("tracking.user_agent.upsert", payload)

    def log_event_async(
        self,
        log_type: str = "info",
        filename: str | None = None,
        method: str | None = None,
        args=None,
        kwargs=None,
        message: str | None = None,
        traceback: str | None = None,
    ) -> None:
        if not filename:
            caller = inspect.stack()[1]
            filename = os.path.splitext(os.path.basename(caller.filename))[0]
        if not method:
            method = inspect.stack()[1][3]

        doc = {
            "timestamp": datetime.now(timezone.utc),
            "type": log_type,
            "filename": filename,
            "method": method,
            "args": args,
            "kwargs": kwargs,
            "message": message,
            "traceback": traceback,
        }
        self.jobs.enqueue("tracking.event.write", doc)

    def update_visitor_id_async(self, *, session_id: str, visitor_id: str) -> None:
        self.jobs.enqueue(
            "tracking.visitor_id.propagate",
            {"session_id": session_id, "visitor_id": visitor_id},
        )

    # ---------- Sync reads (dashboards/admin) ----------
    def get_user_activities(self, start_date, end_date) -> list[dict]:
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.user_activity_log.name,
            size=10000,
            query={"range": {"timestamp": {"gte": start_date, "lte": end_date}}},
            sort=[{"timestamp": "desc"}],
        )
        return result["hits"]["hits"]

    def get_search_terms(self, start_date, end_date) -> list[dict]:
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.search_term_log.name,
            size=10000,
            query={"range": {"timestamp": {"gte": start_date, "lte": end_date}}},
            sort=[{"timestamp": "desc"}],
        )
        return result["hits"]["hits"]

    def get_user_agents(self, start_date, end_date, timestamp_field: str = "timestamp_updated") -> list[dict]:
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.user_agent_log.name,
            size=10000,
            query={"range": {timestamp_field: {
                "gte": start_date, "lte": end_date}}},
            sort=[{timestamp_field: "desc"}],
        )
        return result["hits"]["hits"]

    def get_events(self, start_date, end_date, log_type: str) -> list[dict]:
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.event_logs.name,
            size=10000,
            query={
                "bool": {
                    "must": [
                        {"term": {"type.keyword": log_type}},
                        {"range": {"timestamp": {"gte": start_date, "lte": end_date}}},
                    ]
                }
            },
            sort=[{"timestamp": "desc"}],
        )
        return result["hits"]["hits"]

    def delete_event(self, event_id: str) -> None:
        self.es.delete(index=ESIndex.event_logs.name, id=event_id)
