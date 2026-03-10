from __future__ import annotations

from datetime import date, datetime
import pandas as pd

from nfdi_search_engine.common.dates import to_es_range
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.user_service import UserService

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


class AnalyticsService:
    def __init__(self, tracking_service: TrackingService, user_service: UserService, *, es_date_format: str):
        self.tracking = tracking_service
        self.users = user_service
        self.es_date_format = es_date_format

    # ---------- Public dashboard summaries ----------
    def generate_registered_users_summaries(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        es_start, es_end = to_es_range(year_start, today, self.es_date_format)
        current_year_users = self.users.list_users_between(es_start, es_end)

        df = pd.json_normalize(current_year_users)
        if df.empty or "_source.timestamp_created" not in df.columns:
            return self._empty_month_day_summary()

        df = df[["_id", "_source.timestamp_created"]].rename(
            columns={"_id": "id", "_source.timestamp_created": "timestamp"}
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")
        df = df.dropna(subset=["timestamp"])

        # yearly monthly summary
        df["month"] = df["timestamp"].dt.month_name()
        grouped = df.groupby("month")["id"].nunique()
        result_df = pd.DataFrame(grouped).reset_index().rename(columns={"id": "Unique ID count"})
        result_df = result_df.set_index("month").reindex(_MONTHS).fillna(0).reset_index()
        result_df = result_df.rename(columns={"month": "x", "Unique ID count": "y"})
        current_year_users_series = result_df.to_dict("records")
        current_year_users_count = df.shape[0]

        # current month daily summary
        month_start = pd.to_datetime(today.replace(day=1, hour=0, minute=0, second=0, microsecond=0), utc=True)
        df_month = df[df["timestamp"] > month_start].copy()
        df_month["day"] = df_month["timestamp"].dt.day.astype(int).astype(str).str.zfill(2)

        grouped_day = df_month.groupby("day")["id"].nunique()
        result_df = pd.DataFrame(grouped_day).reset_index().rename(columns={"id": "Unique ID count"})
        all_days = [str(i).zfill(2) for i in range(1, 32)]
        result_df = result_df.set_index("day").reindex(all_days).fillna(0).reset_index()
        result_df = result_df.rename(columns={"day": "x", "Unique ID count": "y"})
        current_month_users = result_df.to_dict("records")
        current_month_users_count = df_month.shape[0]

        return (
            current_month_users,
            current_month_users_count,
            current_year_users_series,
            current_year_users_count,
        )

    def generate_visitors_summaries(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        es_start, es_end = to_es_range(year_start, today, self.es_date_format)
        current_year_visitors = self.tracking.get_user_agents(es_start, es_end, timestamp_field="timestamp_created")

        df = pd.json_normalize(current_year_visitors)
        if df.empty or "_source.timestamp_created" not in df.columns:
            return self._empty_month_day_summary()

        df = df[["_source.visitor_id", "_source.timestamp_created"]].rename(
            columns={"_source.visitor_id": "id", "_source.timestamp_created": "timestamp"}
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")
        df = df.dropna(subset=["timestamp"])

        # yearly monthly summary
        df["month"] = df["timestamp"].dt.month_name()
        grouped = df.groupby("month")["id"].nunique()
        result_df = pd.DataFrame(grouped).reset_index().rename(columns={"id": "Unique ID count"})
        result_df = result_df.set_index("month").reindex(_MONTHS).fillna(0).reset_index()
        result_df = result_df.rename(columns={"month": "x", "Unique ID count": "y"})
        current_year_visitors_series = result_df.to_dict("records")
        current_year_visitors_count = df.shape[0]

        # current month daily summary
        month_start = pd.to_datetime(today.replace(day=1, hour=0, minute=0, second=0, microsecond=0), utc=True)
        df_month = df[df["timestamp"] > month_start].copy()
        df_month["day"] = df_month["timestamp"].dt.day.astype(int).astype(str).str.zfill(2)

        grouped_day = df_month.groupby("day")["id"].nunique()
        result_df = pd.DataFrame(grouped_day).reset_index().rename(columns={"id": "Unique ID count"})
        all_days = [str(i).zfill(2) for i in range(1, 32)]
        result_df = result_df.set_index("day").reindex(all_days).fillna(0).reset_index()
        result_df = result_df.rename(columns={"day": "x", "Unique ID count": "y"})
        current_month_visitors = result_df.to_dict("records")
        current_month_visitors_count = df_month.shape[0]

        return (
            current_month_visitors,
            current_month_visitors_count,
            current_year_visitors_series,
            current_year_visitors_count,
        )

    def generate_user_agent_family_summary(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        es_start, es_end = to_es_range(year_start, today, self.es_date_format)

        hits = self.tracking.get_user_agents(es_start, es_end, timestamp_field="timestamp_created")
        df = pd.json_normalize(hits)
        if df.empty or "_source.user_agent_family" not in df.columns:
            return [], [], 0

        df = df[["_source.visitor_id", "_source.user_agent_family"]].rename(
            columns={"_source.visitor_id": "id", "_source.user_agent_family": "user_agent"}
        )
        df.drop_duplicates(inplace=True)

        grouped = df.groupby("user_agent")["id"].nunique()
        result_df = pd.DataFrame(grouped).reset_index().rename(columns={"id": "Unique ID count"})

        return (
            result_df["Unique ID count"].tolist(),
            result_df["user_agent"].tolist(),
            result_df.shape[0],
        )

    def generate_operating_system_family_summary(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        es_start, es_end = to_es_range(year_start, today, self.es_date_format)

        hits = self.tracking.get_user_agents(es_start, es_end, timestamp_field="timestamp_created")
        df = pd.json_normalize(hits)
        if df.empty or "_source.os_family" not in df.columns:
            return [], [], 0

        df = df[["_source.visitor_id", "_source.os_family"]].rename(
            columns={"_source.visitor_id": "id", "_source.os_family": "os"}
        )
        df.drop_duplicates(inplace=True)

        grouped = df.groupby("os")["id"].nunique()
        result_df = pd.DataFrame(grouped).reset_index().rename(columns={"id": "Unique ID count"})

        return (
            result_df["Unique ID count"].tolist(),
            result_df["os"].tolist(),
            result_df.shape[0],
        )

    def generate_search_term_summary(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        es_start, es_end = to_es_range(year_start, today, self.es_date_format)

        hits = self.tracking.get_search_terms(es_start, es_end)
        df = pd.json_normalize(hits)
        if df.empty or "_source.search_term" not in df.columns:
            return {}

        df = df[["_id", "_source.search_term"]].rename(columns={"_id": "id", "_source.search_term": "search_term"})
        grouped = df.groupby("search_term")["id"].count()
        top10 = pd.DataFrame(grouped).reset_index().rename(columns={"id": "count"}).nlargest(10, "count")
        return top10.set_index("search_term").T.to_dict("list")

    def generate_traffic_summary(self):
        today = datetime.today()
        year_start = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        es_start, es_end = to_es_range(year_start, today, self.es_date_format)

        hits = self.tracking.get_user_activities(es_start, es_end)
        df = pd.json_normalize(hits)
        if df.empty or "_source.timestamp" not in df.columns:
            return [0] * 12, [0] * 12

        df = df[["_id", "_source.user_email", "_source.timestamp"]].rename(
            columns={"_id": "id", "_source.user_email": "email", "_source.timestamp": "timestamp"}
        )
        df.fillna("", inplace=True)
        df["user_type"] = df["email"].apply(lambda x: "visitor" if x == "" else "registered user")
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601", errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["month"] = df["timestamp"].dt.month_name()

        grouped = df.groupby(["user_type", "month"])["id"].size()
        result_df = pd.DataFrame(grouped).reset_index().rename(columns={"id": "count"})

        reg = result_df[result_df["user_type"] == "registered user"][["month", "count"]].set_index("month")
        vis = result_df[result_df["user_type"] == "visitor"][["month", "count"]].set_index("month")

        reg = reg.reindex(_MONTHS).fillna(0).reset_index()
        vis = vis.reindex(_MONTHS).fillna(0).reset_index()

        return reg["count"].tolist(), vis["count"].tolist()

    # ---------- helpers ----------
    def _empty_month_day_summary(self):
        empty_month = [{"x": m, "y": 0} for m in _MONTHS]
        empty_days = [{"x": str(i).zfill(2), "y": 0} for i in range(1, 32)]
        return empty_days, 0, empty_month, 0
