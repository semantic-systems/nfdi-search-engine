from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from elasticsearch import Elasticsearch, exceptions
from nfdi_search_engine.common.models.user import User
from nfdi_search_engine.infra.elastic.indices import ESIndex
from nfdi_search_engine.common.dates import to_es_range


class UserService:
    """
    Service for registered user persistence and preference management.

    This service provides the application-level API for:
    - Creating users (including default data-source inclusion)
    - Updating user profile fields (name, oauth source)
    - Updating user preferences (included/excluded data sources)
    - Looking up users by id or email
    - Deleting users
    - Listing users within a date range (for control-panel reporting)
    """
    def __init__(self, es_client: Elasticsearch, all_data_sources: list[str], es_date_format: str = "%Y-%m-%d"):
        """
        Initialize the user service.

        :param es_client: Elasticsearch client used for user CRUD operations.
        :type es_client: Elasticsearch
        :param all_data_sources: List of all configured data source keys. Used to
            initialize default included sources on user creation.
        :type all_data_sources: list[str]
        :param es_date_format: Date format used to convert date/datetime ranges to ES query strings.
        :type es_date_format: str
        """
        self.es = es_client
        self.all_data_sources = all_data_sources
        self.es_date_format = es_date_format

    # ---------- Public API ----------
    def create_user(self, user: User) -> None:
        """
        Create a new user record in Elasticsearch.

        :param user: User object to persist.
        :type user: User
        :return: None
        :rtype: None
        """
        doc = user.to_dict()
        doc["timestamp_created"] = datetime.now(timezone.utc)
        doc["included_data_sources"] = "; ".join(self.all_data_sources)
        doc["excluded_data_sources"] = user.excluded_data_sources or ""

        self.es.index(index=ESIndex.users.name, document=doc)

    def update_user_profile(self, user: User) -> None:
        """
        Update basic user profile fields.

        Updates:
        - first_name
        - last_name
        - oauth_source
        - timestamp_updated (UTC)

        :param user: User object with updated fields (must contain id).
        :type user: User
        :return: None
        :rtype: None
        """
        self.es.update(
            index=ESIndex.users.name,
            id=user.id,
            doc={
                "first_name": user.first_name,
                "last_name": user.last_name,
                "oauth_source": user.oauth_source,
                "timestamp_updated": datetime.now(timezone.utc),
            },
        )

    def update_user_preferences(self, user: User) -> None:
        """
        Update user data-source preferences.

        Updates:
        - included_data_sources
        - excluded_data_sources
        - timestamp_updated (UTC)

        :param user: User object with updated preference fields (must contain id).
        :type user: User
        :return: None
        :rtype: None
        """
        self.es.update(
            index=ESIndex.users.name,
            id=user.id,
            doc={
                "included_data_sources": user.included_data_sources,
                "excluded_data_sources": user.excluded_data_sources,
                "timestamp_updated": datetime.now(timezone.utc),
            },
        )

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by Elasticsearch document id.

        :param user_id: Elasticsearch user document id.
        :type user_id: str
        :return: User object if found, else None.
        :rtype: Optional[User]
        """
        doc = self._get_user_doc_by_id(user_id)
        return None if doc is None else User.from_dict(doc)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieve a user by unique email address.

        Uses an exact-match term query on ``email.keyword``. Returns None if
        no unique record is found.

        :param email: User email address.
        :type email: str
        :return: User object if found, else None.
        :rtype: Optional[User]
        """
        doc = self._get_user_doc_by_email(email)
        return None if doc is None else User.from_dict(doc)

    def delete_user(self, user_id: str) -> None:
        """
        Delete a user record by Elasticsearch document id.

        :param user_id: Elasticsearch user document id.
        :type user_id: str
        :return: None
        :rtype: None
        """
        self.es.delete(index=ESIndex.users.name, id=user_id)

    def list_users_between(self, start_date, end_date) -> list[dict]:
        """
        List raw user documents created within a date range.

        This is primarily used by control-panel reporting views. The returned
        payload matches the raw Elasticsearch hit format.

        :param start_date: Range start date/datetime (or compatible input for ``to_es_range``).
        :type start_date: Any
        :param end_date: Range end date/datetime (or compatible input for ``to_es_range``).
        :type end_date: Any
        :return: Raw Elasticsearch hit list for matching users.
        :rtype: list[dict]
        """
        start_date, end_date = to_es_range(start_date, end_date, self.es_date_format)
        result = self.es.search(
            index=ESIndex.users.name,
            size=10000,
            query={
                "range": {
                    "timestamp_created": {
                        "gte": start_date,
                        "lte": end_date,
                    }
                }
            },
            sort=[{"timestamp_created": {"order": "desc", "unmapped_type": "date"}}],
        )
        return result["hits"]["hits"]

    # ---------- Private ES helpers ----------
    def _get_user_doc_by_id(self, user_id: str) -> dict | None:
        """
        Internal helper to fetch a user document by id and normalize the hit format.

        :param user_id: Elasticsearch document id.
        :type user_id: str
        :return: Flattened dict containing ``id`` plus ES ``_source`` fields, or None.
        :rtype: dict | None
        """
        try:
            hit = self.es.get(index=ESIndex.users.name, id=user_id)
            return {"id": hit["_id"], **hit["_source"]}
        except exceptions.NotFoundError:
            return None
        except Exception:
            return None

    def _get_user_doc_by_email(self, email: str) -> dict | None:
        """
        Internal helper to fetch a user document by email address.

        :param email: Email address to search (exact match).
        :type email: str
        :return: Flattened dict containing ``id`` plus ES ``_source`` fields, or None.
        :rtype: dict | None
        """
        result = self.es.search(
            index=ESIndex.users.name,
            query={"term": {"email.keyword": email}},
            size=2,
        )
        if int(result["hits"]["total"]["value"]) != 1:
            return None

        hit = result["hits"]["hits"][0]
        return {"id": hit["_id"], **hit["_source"]}
