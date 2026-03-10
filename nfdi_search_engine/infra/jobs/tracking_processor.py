from __future__ import annotations

from elasticsearch import Elasticsearch

from nfdi_search_engine.infra.elastic.indices import ESIndex


class TrackingProcessor:
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client

    def handle_write_activity(self, doc: dict) -> None:
        self.es.index(index=ESIndex.user_activity_log.name, document=doc)

    def handle_write_search_term(self, doc: dict) -> None:
        self.es.index(index=ESIndex.search_term_log.name, document=doc)

    def handle_write_event(self, doc: dict) -> None:
        self.es.index(index=ESIndex.event_logs.name, document=doc)

    def handle_upsert_user_agent(self, doc: dict) -> None:
        session_id = doc.get("session_id", "")
        result = self.es.search(
            index=ESIndex.user_agent_log.name,
            query={"match": {"session_id": {"query": session_id}}},
            size=1,
        )

        total = int(result["hits"]["total"]["value"])
        if total > 0:
            hit = result["hits"]["hits"][0]
            self.es.update(
                index=ESIndex.user_agent_log.name,
                id=hit["_id"],
                doc={
                    "timestamp_updated": doc.get("timestamp_updated"),
                    "url": doc.get("url", ""),
                },
            )
            return

        self.es.index(index=ESIndex.user_agent_log.name, document=doc)

    def handle_propagate_visitor_id(self, payload: dict) -> None:
        session_id = payload.get("session_id", "")
        visitor_id = payload.get("visitor_id", "")
        if not session_id:
            return

        self._update_missing_visitor_ids(
            ESIndex.user_activity_log.name, session_id, visitor_id)
        self._update_missing_visitor_ids(
            ESIndex.search_term_log.name, session_id, visitor_id)
        self._update_missing_visitor_ids(
            ESIndex.user_agent_log.name, session_id, visitor_id)

    def _update_missing_visitor_ids(self, index_name: str, session_id: str, visitor_id: str) -> None:
        result = self.es.search(
            index=index_name,
            size=10000,
            query={
                "bool": {
                    "must": [
                        {"term": {"session_id.keyword": session_id}},
                        {"term": {"visitor_id.keyword": ""}},
                    ]
                }
            },
        )
        for hit in result["hits"]["hits"]:
            self.es.update(
                index=index_name, id=hit["_id"],
                doc={"visitor_id": visitor_id}
            )
