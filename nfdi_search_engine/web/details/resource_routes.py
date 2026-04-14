from __future__ import annotations

from flask import abort, current_app, jsonify, make_response, render_template, request, session
from flask_login import current_user

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.details import bp
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.web.helpers.timestamp_token import validate_ts_token
from nfdi_search_engine.web.helpers.params import parse_prefixed_and_unquote
from nfdi_search_engine.web.decorators import set_cookies, timeit
from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.resource_details_service import ResourceDetailsService


def _get_services() -> tuple[ResourceDetailsService, TrackingService]:
    s = current_app.extensions["services"]
    return s["resource_details"], s["tracking"]


@bp.route(
    "/resource-details/<string:source_name>/<string:doi>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@timeit
@set_cookies
def resource_details(source_name, doi, ts):
    """
    Render the resource details page.
    
    :param source_name: The source name string
    :param doi: The doi string
    :param ts: timestamp for bot id
    """
    resource_details_svc, tracking = _get_services()

    request_meta = RequestMeta(
        user_email=session.get("current-user-email", ""),
        session_id=session.get("gateway-session-id", ""),
        visitor_id=session.get("visitor_id", ""),
        url=request.url,
        host=request.host,
        url_root=request.root_url,
        base_url=request.base_url,
        path=request.path,
        client_ip=get_client_ip(),
    )

    tracking.log_activity_async(
        description=f"loading resource details page: {doi}",
        request_meta=request_meta,
        user_id=(current_user.get_id()
                 if not current_user.is_anonymous else None),
    )

    source_name = parse_prefixed_and_unquote(source_name)
    doi = parse_prefixed_and_unquote(doi)
    ts = parse_prefixed_and_unquote(ts)

    # timestamp signature for bot id
    validate_ts_token(ts)

    try:
        resource = resource_details_svc.get_resource_details(
            doi=doi,
            source_name=source_name,
        )

        if not resource:
            raise ValueError(f"Couldnt find resource details for doi {doi} in {source_name}")
    except Exception as ex:
        tracking.log_event_async(
            log_type="error",
            message=(
                "resource_details - failed to load resource: "
                f"source_name={source_name}, doi={doi}, "
                f"error={str(ex)}"
            ),
        )
        return make_response(render_template("no-results.html", type="resource", identifier=doi))

    return make_response(render_template("resource-details.html", resource=resource))
