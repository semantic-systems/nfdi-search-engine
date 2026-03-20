from __future__ import annotations

import hmac
import os

from nfdi_search_engine.web.control_panel import bp
from flask import Blueprint, Response, current_app, jsonify, render_template, request

from nfdi_search_engine.common.dates import parse_report_date_range, to_es_range
from nfdi_search_engine.services.analytics_service import AnalyticsService
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.user_service import UserService



def _check_auth() -> bool:
    """
    Validate HTTP Basic Auth credentials for the control panel.

    :return: True if valid credentials are present, otherwise False.
    """
    dashboard_username = os.environ.get("DASHBOARD_USERNAME")
    dashboard_password = os.environ.get("DASHBOARD_PASSWORD")

    if not dashboard_username or not dashboard_password:
        current_app.logger.warning(
            "Dashboard username or password not set in environment variables.")
        return False

    auth = request.authorization
    if not auth or (auth.type or "").lower() != "basic":
        return False

    return hmac.compare_digest(auth.username, dashboard_username) and hmac.compare_digest(
        auth.password, dashboard_password
    )


@bp.before_request
def dashboard_auth():
    """
    Enforce HTTP Basic Auth for all control-panel routes.

    Allows OPTIONS requests (e.g., CORS preflight) without authentication.
    """
    if request.method == "OPTIONS":
        return None

    if not _check_auth():
        return Response(
            "Authentication required",
            401,
            {"WWW-Authenticate": 'Basic realm="Control Panel"'},
        )
    return None


def _get_services() -> tuple[AnalyticsService, TrackingService, UserService]:
    s = current_app.extensions["services"]
    return s["analytics"], s["tracking"], s["users"]


def _report_range(report_date_range: str | None):
    """
    Parse a control-panel date range token and return both display and ES ranges.

    :param report_date_range: Optional URL token identifying the report range.
    :return: Tuple(start_date, end_date, es_start, es_end, report_daterange_str)
    """
    start_date, end_date = parse_report_date_range(report_date_range)
    es_start, es_end = to_es_range(
        start_date, end_date, current_app.config["DATE_FORMAT_FOR_ELASTIC"])
    report_daterange = (
        f"{start_date.strftime(current_app.config['DATE_FORMAT_FOR_REPORT'])} - "
        f"{end_date.strftime(current_app.config['DATE_FORMAT_FOR_REPORT'])}"
    )
    return start_date, end_date, es_start, es_end, report_daterange


@bp.route("/dashboard")
def dashboard():
    """
    Render the control-panel dashboard.

    Aggregates multiple summary series (registered users, visitors, UA/OS families,
    search terms, traffic) via AnalyticsService and renders the dashboard template.

    :return: rendered dashboard template
    """
    analytics, _, _ = _get_services()

    (
        current_month_users,
        current_month_users_count,
        current_year_users,
        current_year_users_count,
    ) = analytics.generate_registered_users_summaries()

    (
        current_month_visitors,
        current_month_visitors_count,
        current_year_visitors,
        current_year_visitors_count,
    ) = analytics.generate_visitors_summaries()

    current_year_ua_series, current_year_ua_labels, current_year_ua_count = analytics.generate_user_agent_family_summary()
    current_year_os_series, current_year_os_labels, current_year_os_count = analytics.generate_operating_system_family_summary()
    current_year_search_terms = analytics.generate_search_term_summary()
    current_year_traffic_registered_users, current_year_traffic_visitors = analytics.generate_traffic_summary()

    return render_template("control-panel/dashboard.html", **locals())


@bp.route("/activity-log", defaults={"report_date_range": None})
@bp.route("/activity-log/<report_date_range>")
def activity_log(report_date_range):
    """
    Render the activity log report for a given date range.

    :param report_date_range: Optional URL token identifying the report range.
    :return: rendered activity log template
    """
    _, _, es_start, es_end, report_daterange = _report_range(report_date_range)
    _, tracking, _ = _get_services()
    user_activities = tracking.get_user_activities(es_start, es_end)
    return render_template(
        "control-panel/activity-log.html",
        user_activities=user_activities,
        report_daterange=report_daterange,
    )


@bp.route("/user-agent-log", defaults={"report_date_range": None})
@bp.route("/user-agent-log/<report_date_range>")
def user_agent_log(report_date_range):
    """
    Render the user-agent log report for a given date range.

    :param report_date_range: Optional URL token identifying the report range.
    :return: rendered user-agent log template
    """
    _, _, es_start, es_end, report_daterange = _report_range(report_date_range)
    _, tracking, _ = _get_services()
    user_agents = tracking.get_user_agents(es_start, es_end)
    return render_template(
        "control-panel/agent-log.html",
        user_agents=user_agents,
        report_daterange=report_daterange,
    )


@bp.route("/event-log/<log_type>", defaults={"report_date_range": None})
@bp.route("/event-log/<log_type>/<report_date_range>")
def event_log(log_type, report_date_range):
    """
    Render the event log report for a given log type and date range.

    :param log_type: Event severity/type filter (e.g., "error", "warning", "info").
    :param report_date_range: Optional URL token identifying the report range.
    :return: rendered event log template
    """
    _, _, es_start, es_end, report_daterange = _report_range(report_date_range)
    _, tracking, _ = _get_services()
    events = tracking.get_events(es_start, es_end, log_type)
    return render_template(
        "control-panel/event-log.html",
        events=events,
        log_type=log_type,
        report_daterange=report_daterange,
    )


@bp.route("/event-log/delete-event", methods=["POST"])
def delete_event():
    """
    Delete a single event log record by id.
    Expects ``event_id`` in form values.

    :return: JSON confirmation response.
    """
    event_id = request.values.get("event_id")
    _, tracking, _ = _get_services()
    tracking.delete_event(event_id)
    return jsonify({"message": "Event has been deleted"}), 200


@bp.route("/registered-users", defaults={"report_date_range": None})
@bp.route("/registered-users/<report_date_range>")
def registered_users(report_date_range):
    """
    Render the registered users report for a given date range.

    :param report_date_range: Optional URL token identifying the report range.
    :return: rendered registered users template
    """
    _, _, es_start, es_end, report_daterange = _report_range(report_date_range)
    _, _, users_service = _get_services()
    users = users_service.list_users_between(es_start, es_end)
    return render_template(
        "control-panel/registered-users.html",
        users=users,
        report_daterange=report_daterange,
    )


@bp.route("/registered-users/delete-user/<string:user_id>")
def delete_user(user_id):
    """
    Delete a registered user by id.

    :param user_id: Elasticsearch user document id.
    :return: Plain-text confirmation string.
    """
    _, _, users_service = _get_services()
    users_service.delete_user(user_id)
    return "User has been deleted"


@bp.route("/search-term-log", defaults={"report_date_range": None})
@bp.route("/search-term-log/<report_date_range>")
def search_term_log(report_date_range):
    """
    Render the search term log report for a given date range.

    :param report_date_range: Optional URL token identifying the report range.
    :return: rendered search-term log template
    """
    _, _, es_start, es_end, report_daterange = _report_range(report_date_range)
    _, tracking, _ = _get_services()
    search_terms = tracking.get_search_terms(es_start, es_end)
    return render_template(
        "control-panel/search-term-log.html",
        search_terms=search_terms,
        report_daterange=report_daterange,
    )
