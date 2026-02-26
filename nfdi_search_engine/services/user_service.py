from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from elasticsearch import Elasticsearch, exceptions
from nfdi_search_engine.common.user import User
from nfdi_search_engine.infra.elastic.indices import ESIndex
from nfdi_search_engine.util.dates import to_es_range


class UserService:
    def __init__(self, es_client: Elasticsearch, all_data_sources: list[str], es_date_format: str = "%Y-%m-%d"):
        self.es = es_client
        self.all_data_sources = all_data_sources
        self.es_date_format = es_date_format

    # ---------- Public API ----------
    def create_user(self, user: User) -> None:
        doc = user.to_dict()
        doc["timestamp_created"] = datetime.now(timezone.utc)
        doc["included_data_sources"] = "; ".join(self.all_data_sources)
        doc["excluded_data_sources"] = user.excluded_data_sources or ""

        self.es.index(index=ESIndex.USERS.value, document=doc)

    def update_user_profile(self, user: User) -> None:
        self.es.update(
            index=ESIndex.USERS.value,
            id=user.id,
            doc={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "oauth_source": user.oauth_source,
                "timestamp_updated": datetime.now(timezone.utc),
            },
        )

    def update_user_preferences(self, user: User) -> None:
        self.es.update(
            index=ESIndex.USERS.value,
            id=user.id,
            doc={
                "included_data_sources": user.included_data_sources,
                "excluded_data_sources": user.excluded_data_sources,
                "timestamp_updated": datetime.now(timezone.utc),
            },
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        doc = self._get_user_doc_by_id(user_id)
        return None if doc is None else User.from_dict(doc)

    def get_user_by_email(self, email: str) -> Optional[User]:
        doc = self._get_user_doc_by_email(email)
        return None if doc is None else User.from_dict(doc)

    def delete_user(self, user_id: str) -> None:
        self.es.delete(index=ESIndex.USERS.value, id=user_id)

    def list_users_between(self, start_date, end_date) -> list[dict]:
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.USERS.value,
            size=10000,
            query={
                "range": {
                    "timestamp_created": {
                        "gte": start_date,
                        "lte": end_date,
                    }
                }
            },
            sort=[{"timestamp_created": "desc"}],
        )
        return result["hits"]["hits"]

    # ---------- Private ES helpers ----------
    def _get_user_doc_by_id(self, user_id: str) -> dict | None:
        try:
            hit = self.es.get(index=ESIndex.USERS.value, id=user_id)
            return {"id": hit["_id"], **hit["_source"]}
        except exceptions.NotFoundError:
            return None
        except Exception:
            return None

    def _get_user_doc_by_email(self, email: str) -> dict | None:
        result = self.es.search(
            index=ESIndex.USERS.value,
            query={"term": {"email.keyword": email}},
            size=2,
        )
        if int(result["hits"]["total"]["value"]) != 1:
            return None

        hit = result["hits"]["hits"][0]
        return {"id": hit["_id"], **hit["_source"]}
