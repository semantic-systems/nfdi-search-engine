from __future__ import annotations

from urllib.parse import unquote
import base64
import time

from flask import abort, current_app, jsonify, make_response, render_template, request, session
from flask_login import current_user

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.details import bp
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.web.helpers.timestamp_token import validate_ts_token
from nfdi_search_engine.web.helpers.params import parse_prefixed_and_unquote
from nfdi_search_engine.web.decorators import set_cookies, timeit
from nfdi_search_engine.common.request_meta import RequestMeta
from nfdi_search_engine.services.publication_details_service import PublicationDetailsService
from nfdi_search_engine.services.tracking_service import TrackingService


def _get_services() -> tuple[PublicationDetailsService, TrackingService]:
    s = current_app.extensions["services"]
    return s["publication_details"], s["tracking"]


@bp.route("/publication-details/get-dois-references/<path:doi>", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_dois_references(doi):
    """
    Endpoint to get a list of references for a given DOI in JSON format.
    
    :param doi: The DOI string
    """
    svc, _ = _get_services()
    dois = svc.get_reference_dois(doi)
    return jsonify({"dois": dois})


@bp.route("/publication-details/get-dois-citations/<path:doi>", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_citations_dois(doi):
    """
    Endpoint to get a list of citations for a given DOI in JSON format.
    
    :param doi: The DOI string
    """
    svc, _ = _get_services()
    dois = svc.get_citation_dois(doi)
    return jsonify({"dois": dois})


@bp.route("/publication-details/get-metadata/", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_metadata():
    """
    Endpoint to get metadata for a list of DOIs in JSON format.
    """
    body = request.get_json(silent=True) or {}
    dois = body.get("dois", []) or []
    if not dois:
        return jsonify({"error": "No DOIs provided"}), 400

    svc, _ = _get_services()
    payload = svc.get_metadata_for_dois(dois)
    return jsonify({"publications": payload})


@bp.route(
    "/publication-details/<string:source_name>/<string:doi>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@timeit
@set_cookies
def publication_details(source_name, doi, ts):
    """
    Render the publication details page.
    
    :param source_name: The source name string
    :param doi: The DOI string
    :param ts: timestamp for bot id
    """
    pub_svc, tracking_svc = _get_services()

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

    tracking_svc.log_activity_async(
        description=f"loading publication details page: {doi}/",
        request_meta=request_meta,
        user_id=None if current_user.is_anonymous else current_user.id,
    )

    source_name = parse_prefixed_and_unquote(source_name)
    doi = parse_prefixed_and_unquote(doi)
    ts = parse_prefixed_and_unquote(ts)

    # timestamp signature for bot id
    validate_ts_token(ts)

    excluded_sources = set()
    if not current_user.is_anonymous:
        excluded_sources = {s for s in (
            current_user.excluded_data_sources or "").split("; ") if s}

    publications, failed = pub_svc.get_publications_for_details_page(
        doi=doi,
        excluded_sources=excluded_sources,
    )

    if not publications:
        return make_response(render_template("no-results.html", type="publication", identifier=doi))

    merged = pub_svc.merge_publications(publications)
    return make_response(render_template("publication-details.html", publication=merged))


@bp.route("/publication-details-citations/<path:doi>", methods=["GET"])
@timeit
def publication_details_citations(doi):
    """
    Render citations partial for a DOI.
    
    :param doi: The DOI string
    """
    svc, _ = _get_services()
    pubs = svc.get_citations_for_publication(doi)
    return make_response(
        render_template(
            "partials/publication-details/citations.html", publications=pubs)
    )


@bp.route("/publication-details-recommendations/<path:doi>", methods=["GET"])
@timeit
def publication_details_recommendations(doi):
    """
    Render recommendations partial for a DOI.
    
    :param doi: The DOI string
    """
    svc, _ = _get_services()
    pubs = svc.get_recommendations_for_publication(doi)
    return make_response(
        render_template(
            "partials/publication-details/recommendations.html", publications=pubs)
    )


@bp.get("/publication-details/citation/format")
@limiter.limit("10 per minute")
def get_citation():
    """
    Format a DOI citation using citation.doi.org.
    """
    doi = (request.args.get("doi") or "").strip().lower()
    style = (request.args.get("style") or "ieee").strip()

    if not doi:
        return jsonify({"error": "missing doi"}), 400

    svc, _ = _get_services()
    try:
        return jsonify(svc.format_citation(doi=doi, style=style)), 200
    except Exception as e:
        return jsonify({"error": "citation service failed", "detail": str(e)}), 502
