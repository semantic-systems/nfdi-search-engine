from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Tuple
from dateparser import parse


def parse_report_date_range(report_date_range: str | None) -> tuple[date, date]:
    today = date.today()

    if not report_date_range:
        return today.replace(day=1), today

    token = report_date_range.strip().lower()

    if token == "today":
        return today, today

    if token == "yesterday":
        y = today - timedelta(days=1)
        return y, y

    if token in {"this-month", "current-month"}:
        return today.replace(day=1), today

    if token in {"this-year", "current-year"}:
        return date(today.year, 1, 1), today

    if "_" in token:
        start_s, end_s = token.split("_", 1)
    elif ".." in token:
        start_s, end_s = token.split("..", 1)
    else:
        # fallback: treat as a single day
        d = date.fromisoformat(token)
        return d, d

    return date.fromisoformat(start_s), date.fromisoformat(end_s)


def to_es_range(start_date, end_date, date_format: str) -> tuple[str, str]:
    if isinstance(start_date, str):
        start_dt = parse(start_date)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_dt = datetime.combine(start_date, datetime.min.time())
    else:
        start_dt = start_date

    if isinstance(end_date, str):
        end_dt = parse(end_date)
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_dt = datetime.combine(end_date, datetime.max.time())
    else:
        end_dt = end_date

    return start_dt.strftime(date_format), end_dt.strftime(date_format)


def parse_date(date_str):
    try:
        parsed_date_str = parse(date_str).strftime("%Y-%m-%d")
        return parsed_date_str
    except (TypeError, ValueError):
        print(f"original date str: {date_str}")
        return ""
