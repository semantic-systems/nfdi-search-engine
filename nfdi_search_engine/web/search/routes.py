from __future__ import annotations

import uuid
from typing import Set

from flask import (
    abort,
    current_app,
    flash,
    render_template,
    request,
    session,
)
from flask_login import current_user

from nfdi_search_engine.web.search import bp
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.common.models.request_meta import RequestMeta
from nfdi_search_engine.web import decorators

from nfdi_search_engine.extensions import limiter

from nfdi_search_engine.services.search_service import (
    SearchContext,
    SearchService,
)


def _get_service() -> SearchService:
    return current_app.extensions["services"]["search"]


@bp.route("/results", methods=["GET"])
@limiter.limit("3 per minute")
@decorators.timeit
@decorators.set_cookies
def search_results():
    """
    Render the main search results page.

    Executes a full search across all enabled sources for the query in
    ``txtSearchTerm``. Results are harvested in parallel by the SearchService,
    ranked per category, stored in the ResultStore under a new ``search_uuid``,
    and rendered as the first page slice.

    Side effects:
    - stores ``search-term``, ``back-url`` and ``search_uuid`` in session
    - emits tracking events for activity + search term

    Query params:
    - txtSearchTerm: search query string

    :return: rendered results page template
    """
    search_term = request.args.get("txtSearchTerm", "")
    session["search-term"] = search_term
    session["back-url"] = request.url

    excluded: Set[str] = set()
    if not current_user.is_anonymous:
        excluded = {s for s in (
            current_user.excluded_data_sources or "").split("; ") if s}

    search_id = uuid.uuid4().hex
    session["search_uuid"] = search_id

    meta = RequestMeta(
        url=request.url,
        host=request.host,
        url_root=request.root_url,
        base_url=request.base_url,
        path=request.path,
        user_email=session.get("current-user-email", ""),
        session_id=session.get("gateway-session-id", ""),
        visitor_id=session.get("visitor_id", ""),
        client_ip=get_client_ip(),
    )

    svc = _get_service()
    page = svc.run_search(
        SearchContext(
            search_id=search_id,
            search_term=search_term,
            excluded_sources=excluded,
            request_meta=meta,
            user_id=None if current_user.is_anonymous else current_user.id,
        )
    )

    if page.failed_sources:
        flash(
            f"Following sources could not be harvested: {', '.join(page.failed_sources)}",
            category="error",
        )

    return render_template(
        "results.html",
        results=page.results,
        total_results=page.total_results,
        displayed_results=page.displayed_results,
        search_term=page.search_term,
    )


@bp.route(
    "/update_search_result/<string:source>/<string:source_identifier>/<path:doi>",
    methods=["GET"],
)
def update_search_result(source: str, source_identifier: str, doi: str):
    """
    Refresh a single search result block and return the rendered HTML partial.
    Used for in-place updates of result items (e.g., AJAX refresh).

    :param source: configured source key (must exist in settings.data_sources)
    :param source_identifier: source-specific identifier for the resource (passed through for logging/context)
    :param doi: DOI string (may be prefixed with "DOI:")
    :return: rendered resource block partial
    """
    svc = _get_service()
    try:
        resource = svc.update_search_result_block(
            source, source_identifier, doi)
    except KeyError:
        abort(404)

    return render_template("partials/search-results/resource-block.html", resource=resource)


@bp.route(
    "/load-more/<string:object_type>",
    methods=["GET"]
)
def load_more(object_type: str):
    """
    Lazy-load additional search results for a single category and return an HTML partial.

    Reads the current ``search_uuid`` from session and requests the next chunk for
    ``object_type`` from the SearchService (which loads from the ResultStore and
    updates the per-category displayed counter).

    :param object_type: result category (must be one of the configured CATEGORIES)
    :return: rendered category partial with appended items and updated counters
    """
    search_id = session.get("search_uuid")
    if not search_id:
        abort(400, description="Missing search_uuid in session")

    meta = RequestMeta(
        url=request.url,
        host=request.host,
        url_root=request.root_url,
        base_url=request.base_url,
        path=request.path,
        user_email=session.get("current-user-email", ""),
        session_id=session.get("gateway-session-id", ""),
        visitor_id=session.get("visitor_id", ""),
        client_ip=get_client_ip(),
    )

    svc = _get_service()
    try:
        chunk, displayed, total = svc.load_more(
            SearchContext(
                search_id=search_id,
                search_term="",
                excluded_sources={},
                request_meta=meta,
                object_type=object_type,
            ))
    except KeyError:
        abort(404)

    displayed_results = {object_type: displayed}
    total_results = {object_type: total}
    results = {object_type: chunk}

    return render_template(
        f"partials/search-results/{object_type}.html",
        results=results,
        displayed_results=displayed_results,
        total_results=total_results,
    )
