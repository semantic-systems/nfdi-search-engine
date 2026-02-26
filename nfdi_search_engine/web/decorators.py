# nfdi_search_engine/web/decorators.py
from __future__ import annotations

import os
import uuid
import inspect
import traceback
from time import time
from functools import wraps

from flask import current_app, make_response, request, session
from flask_login import current_user

from nfdi_search_engine.common.request_meta import RequestMeta
from nfdi_search_engine.web.helpers.user_agent import build_user_agent_doc
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.services.tracking_service import TrackingService


GATEWAY_SESSION_COOKIE_NAME = "session"


def set_cookies(f):
    # this currently does more than only setting cookies
    # maybe we should rename in the future
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = request.cookies.get(
            GATEWAY_SESSION_COOKIE_NAME
        ) or str(uuid.uuid4())
        session["gateway-session-id"] = session_id

        if current_user.is_authenticated:
            session["current-user-email"] = current_user.email
        else:
            session.pop("current-user-email", None)

        response = make_response(f(*args, **kwargs))

        try:
            tracking: TrackingService = current_app.extensions["services"]["tracking"]
            request_meta = RequestMeta(
                user_email=(
                    current_user.email if current_user.is_authenticated else ""
                ),
                session_id=session.get("gateway-session-id", ""),
                visitor_id=session.get("visitor-id", ""),
                url=request.url,
                host=request.host,
                url_root=request.root_url,
                base_url=request.base_url,
                path=request.path,
                client_ip=get_client_ip(),
            )

            tracking.log_user_agent_async(
                user_agent_doc=build_user_agent_doc(request, request_meta)
            )
            tracking.log_activity_async(
                description=f"loading route: {f.__name__}",
                request_meta=request_meta,
                user_id=(
                    current_user.get_id()
                    if current_user.is_authenticated else None
                ),
            )
        except Exception:
            current_app.logger.exception(
                "Failed to enqueue tracking for route %s", f.__name__
            )
        return response

    return decorated_function


def timeit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ts = time()
        result = f(*args, **kwargs)
        te = time()

        try:
            tracking: TrackingService = current_app.extensions["services"]["tracking"]
            filename = os.path.basename(inspect.getfile(f))
            tracking.log_event_async(
                log_type="info",
                filename=filename,
                method=f.__name__,
                message=f"execution time: {(te - ts):.4f} sec",
            )
        except Exception:
            current_app.logger.exception(
                "Failed to enqueue timing event for %s", f.__name__)
        return result
    return decorated_function


def handle_exceptions(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as ex:
            tracking: TrackingService = current_app.extensions["services"]["tracking"]
            filename = os.path.basename(inspect.getfile(f))
            tracking.log_event_async(
                log_type="error",
                filename=filename,
                method=f.__name__,
                message=str(ex),
                traceback=traceback.format_exc(),
            )
            # maybe it would be better to reraise here in the future

    return decorated_function
