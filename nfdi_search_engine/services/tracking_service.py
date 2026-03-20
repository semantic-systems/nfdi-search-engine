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
    """
    Service for tracking, logging, and control-panel reporting.

    This service provides two complementary responsibilities:

    **Asynchronous writes (request path)**
    All logging that is triggered as part of handling a user request is enqueued
    onto the background job dispatcher to avoid increasing request latency. This
    includes:
    - user activity logs (page loads, actions)
    - search term logs
    - user agent logs (upsert by session)
    - application/event logs (errors, warnings, diagnostics)
    - visitor-id propagation across tracking indices

    **Synchronous reads (control panel / analytics)**
    The control-panel routes require read access to the stored logs (activity,
    search terms, user agents, event logs). These operations are performed
    synchronously.
    """
    def __init__(self, es_client: Elasticsearch, jobs: JobDispatcher, es_date_format: str = "%Y-%m-%d"):
        """
        Initialize the tracking service.

        :param es_client: Elasticsearch client used for synchronous read operations.
        :type es_client: Elasticsearch
        :param jobs: Job dispatcher used for asynchronous write operations.
        :type jobs: JobDispatcher
        :param es_date_format: Date format used to convert date/datetime ranges to
            Elasticsearch query strings.
        :type es_date_format: str
        """
        self.es = es_client
        self.jobs = jobs
        self.es_date_format = es_date_format

    def log_activity_async(self, description: str, request_meta: RequestMeta, user_id: str | None = None) -> None:
        """
        Enqueue a user activity log entry.

        This is used for request-level activity such as "loading route", "loading
        search results", and other UI interactions. The payload is enriched with
        request/session metadata from :class:`RequestMeta`.

        :param description: Human-readable activity description.
        :type description: str
        :param request_meta: Request metadata (session id, user email, url, ip, etc.).
        :type request_meta: RequestMeta
        :param user_id: Optional authenticated user id.
        :type user_id: str | None
        :return: None
        :rtype: None
        """
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "description": description,
            "user_id": user_id,
            **asdict(request_meta),
        }
        self.jobs.enqueue("tracking.activity.write", doc)

    def log_search_term_async(self, search_term: str, request_meta: RequestMeta, user_id: str | None = None) -> None:
        """
        Enqueue a search term log entry.

        Records a query string together with request/session metadata.

        :param search_term: Search query string.
        :type search_term: str
        :param request_meta: Request metadata (session id, user email, url, ip, etc.).
        :type request_meta: RequestMeta
        :param user_id: Optional authenticated user id.
        :type user_id: str | None
        :return: None
        :rtype: None
        """
        doc = {
            "timestamp": datetime.now(timezone.utc),
            "search_term": search_term,
            "user_id": user_id,
            **asdict(request_meta),
        }
        self.jobs.enqueue("tracking.search_term.write", doc)

    def log_user_agent_async(self, user_agent_doc: dict) -> None:
        """
        Enqueue a user-agent upsert operation.

        The user-agent payload should be constructed at the web boundary (e.g. via
        a helper such as ``build_user_agent_doc(request, request_meta)``). The
        background worker performs the upsert logic (match by session id and update
        timestamp/url, otherwise insert).

        :param user_agent_doc: JSON-serializable payload containing UA details and
            request/session context (session_id, user_email, visitor_id, ip_address, url, ...).
        :type user_agent_doc: dict
        :return: None
        :rtype: None
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
        """
        Enqueue an application/event log entry.

        This is the generic diagnostic log channel used for error reporting,
        exceptions raised in source modules, and application-level debug signals.
        If ``filename`` or ``method`` are not provided, they are inferred from
        the immediate caller frame.

        :param log_type: Severity/type string (e.g. "info", "warning", "error").
        :type log_type: str
        :param filename: Optional filename or module identifier; inferred if omitted.
        :type filename: str | None
        :param method: Optional method/function name; inferred if omitted.
        :type method: str | None
        :param args: Optional positional arguments context.
        :type args: Any
        :param kwargs: Optional keyword arguments context.
        :type kwargs: Any
        :param message: Optional human-readable message or exception summary.
        :type message: str | None
        :param traceback: Optional traceback string for error cases.
        :type traceback: str | None
        :return: None
        :rtype: None
        """
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
        """
        Enqueue visitor-id propagation for an existing session.

        :param session_id: Session identifier used by tracking logs.
        :type session_id: str
        :param visitor_id: Visitor identifier to set on matching records.
        :type visitor_id: str
        :return: None
        :rtype: None
        """
        self.jobs.enqueue(
            "tracking.visitor_id.propagate",
            {"session_id": session_id, "visitor_id": visitor_id},
        )

    # ---------- Sync reads (dashboards/admin) ----------
    def get_user_activities(self, start_date, end_date) -> list[dict]:
        """
        Retrieve user activity log records within a date range.

        :param start_date: Range start date/datetime.
        :type start_date: Any
        :param end_date: Range end date/datetime.
        :type end_date: Any
        :return: Raw Elasticsearch hit list.
        :rtype: list[dict]
        """
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.user_activity_log.name,
            size=10000,
            query={"range": {"timestamp": {"gte": start_date, "lte": end_date}}},
            sort=[{"timestamp": {"order": "desc", "unmapped_type": "date"}}],
        )
        return result["hits"]["hits"]

    def get_search_terms(self, start_date, end_date) -> list[dict]:
        """
        Retrieve search term log records within a date range.

        :param start_date: Range start date/datetime.
        :type start_date: Any
        :param end_date: Range end date/datetime.
        :type end_date: Any
        :return: Raw Elasticsearch hit list.
        :rtype: list[dict]
        """
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.search_term_log.name,
            size=10000,
            query={"range": {"timestamp": {"gte": start_date, "lte": end_date}}},
            sort=[{"timestamp": {"order": "desc", "unmapped_type": "date"}}],
        )
        return result["hits"]["hits"]

    def get_user_agents(self, start_date, end_date, timestamp_field: str = "timestamp_updated") -> list[dict]:
        """
        Retrieve user-agent log records within a date range.

        :param start_date: Range start date/datetime.
        :type start_date: Any
        :param end_date: Range end date/datetime.
        :type end_date: Any
        :param timestamp_field: Timestamp field to filter and sort by.
        :type timestamp_field: str
        :return: Raw Elasticsearch hit list.
        :rtype: list[dict]
        """
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.user_agent_log.name,
            size=10000,
            query={"range": {timestamp_field: {
                "gte": start_date, "lte": end_date}}},
            sort=[{timestamp_field: {"order": "desc", "unmapped_type": "date"}}],
        )
        return result["hits"]["hits"]

    def get_events(self, start_date, end_date, log_type: str) -> list[dict]:
        """
        Retrieve application/event log records within a date range and filtered by type.

        :param start_date: Range start date/datetime.
        :type start_date: Any
        :param end_date: Range end date/datetime.
        :type end_date: Any
        :param log_type: Event type/severity (e.g. "error", "warning", "info").
        :type log_type: str
        :return: Raw Elasticsearch hit list.
        :rtype: list[dict]
        """
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
            sort=[{"timestamp": {"order": "desc", "unmapped_type": "date"}}],
        )
        return result["hits"]["hits"]

    def delete_event(self, event_id: str) -> None:
        """
        Delete a single event log entry by document id.

        :param event_id: Elasticsearch document id.
        :type event_id: str
        :return: None
        :rtype: None
        """
        self.es.delete(index=ESIndex.event_logs.name, id=event_id)
