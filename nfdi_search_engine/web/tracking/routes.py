from flask import (
    current_app,
    request,
    session,
)

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.tracking import bp
from nfdi_search_engine.web import decorators
from nfdi_search_engine.services.tracking_service import TrackingService


def _get_service() -> TrackingService:
    return current_app.extensions["services"]["tracking"]


@bp.route("/update-visitor-id", methods=["GET"])
@decorators.timeit
def update_visitor_id():
    """
    Update (propagate) a visitor id for the current session across tracking logs.

    Reads ``visitor_id`` from query parameters and the current ``gateway-session-id``
    from session. Enqueues an asynchronous propagation task that updates existing
    tracking documents for this session that still have an empty visitor_id.

    Query params:
    - visitor_id: visitor identifier to attach to existing tracking records

    :return: "True" as a plain string (legacy contract used by frontend).
    """
    visitor_id = request.args.get("visitor_id")
    session_id = session.get("gateway-session-id", "")

    svc = _get_service()
    svc.update_visitor_id_async(
        session_id=session_id,
        visitor_id=visitor_id
    )

    return str(True)
