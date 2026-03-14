from __future__ import annotations

import time
import base64
from urllib.parse import unquote

from flask import abort, current_app, jsonify, make_response, render_template, request, session
from flask_login import current_user

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.details import bp
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.web.helpers.timestamp_token import validate_ts_token
from nfdi_search_engine.web.helpers.params import parse_prefixed_and_unquote
from nfdi_search_engine.web.decorators import set_cookies, timeit
from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.infra.store.kv_store import KVStore
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.researcher_details_service import ResearcherDetailsService

def _get_store() -> KVStore:
    return current_app.extensions["details_store"]

def _get_services() -> tuple[ResearcherDetailsService, TrackingService]:
    s = current_app.extensions["services"]
    return s["researcher_details"], s["tracking"]


@bp.route(
    "/researcher-details/<string:source_name>/<string:orcid>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@timeit
@set_cookies
def researcher_details(source_name, orcid, ts):
    """
    Render the researcher details page.
    
    :param source_name: The source name string
    :param orcid: The ORCID string
    :param ts: timestamp for bot id
    """
    researcher_details_svc, tracking = _get_services()

    request_meta = RequestMeta(
        user_email=session.get("current-user-email", ""),
        session_id=session.get("gateway-session-id", ""),
        visitor_id=session.get("visitor-id", ""),
        url=request.url,
        host=request.host,
        url_root=request.root_url,
        base_url=request.base_url,
        path=request.path,
        client_ip=get_client_ip(),
    )

    tracking.log_activity_async(
        description=f"loading researcher details page: {orcid}",
        request_meta=request_meta,
        user_id=(current_user.get_id()
                 if not current_user.is_anonymous else None),
    )

    source_name = parse_prefixed_and_unquote(source_name)
    orcid = parse_prefixed_and_unquote(orcid)
    ts = parse_prefixed_and_unquote(ts)

    # timestamp signature for bot id
    validate_ts_token(ts)

    excluded_sources = set()
    if not current_user.is_anonymous:
        excluded_sources = {s for s in (
            current_user.excluded_data_sources or "").split("; ") if s}

    researchers, failed = researcher_details_svc.get_researchers_for_details_page(
        orcid=orcid,
        excluded_sources=excluded_sources,
    )

    if not researchers:
        return make_response(render_template("no-results.html", type="researcher", identifier=orcid))

    merged = researcher_details_svc.merge_researchers(researchers)

    # store snapshot for /generate-researcher-about-me
    details_store = _get_store()
    key = f"researcher:{orcid}"

    # store as dict
    if hasattr(merged, "model_dump"):
        snapshot = merged.model_dump(mode="python", exclude_none=True)
    elif isinstance(merged, dict):
        snapshot = merged
    else:
        snapshot = {"obj": str(merged)}

    details_store.put(key, snapshot, ttl_s=int(
        # keep the researcher details in memory for 30 minutes
        current_app.config.get("DETAILS_SNAPSHOT_TTL_S", 30*60))
    )

    return make_response(render_template("researcher-details.html", researcher=merged))


@bp.route("/generate-researcher-about-me/<string:orcid>", methods=["GET"])
def generate_researcher_about_me(orcid: str):
    """
    Generate an 'about me' paragraph based on the provided researcher details using an LLM.
    
    :param orcid: The ORCID string
    :type orcid: str
    """
    details_store = _get_store()
    key = f"researcher:{orcid}"
    snapshot = details_store.get(key)

    if snapshot is None:
        return jsonify(error="Please reload page"), 400

    researcher_details_svc, _ = _get_services()
    try:
        summary = researcher_details_svc.generate_about_me(snapshot)
        return jsonify(summary=summary)
    except Exception as e:
        current_app.logger.exception("About-me generation failed")
        return jsonify(error="about-me generation failed", detail=str(e)), 502
