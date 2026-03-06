from __future__ import annotations

from flask import abort, current_app, request, session

from nfdi_search_engine.web.chatbot import bp
from nfdi_search_engine.web.decorators import timeit
from nfdi_search_engine.web.helpers.ip import get_client_ip
from nfdi_search_engine.common.request_meta import RequestMeta
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.chatbot_service import ChatbotService, ChatContext


def _get_services() -> tuple[ChatbotService, TrackingService]:
    s = current_app.extensions["services"]
    return s["chatbot"], s["tracking"]


@bp.route("/are-embeddings-generated", methods=["GET"])
@timeit
def are_embeddings_generated():
    search_uuid = session.get("search_uuid")
    if not search_uuid:
        abort(400, description="Missing search_uuid in session")

    svc, _ = _get_services()
    ready = svc.are_embeddings_generated(search_uuid=search_uuid)

    return str(bool(ready))


@bp.route("/get-chatbot-answer", methods=["GET"])
@timeit
def get_chatbot_answer():
    question = (request.args.get("question") or "").strip()
    if not question:
        abort(400, description="Missing question")

    search_uuid = session.get("search_uuid")
    if not search_uuid:
        abort(400, description="Missing search_uuid in session")

    chat_context = ChatContext(
        question=question,
        search_uuid=search_uuid,
        request_meta=RequestMeta(
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
    )

    chatbot, _ = _get_services()
    data = chatbot.get_answer(chat_context)

    if data.exception:
        return data.exception

    if not data.chat_history:
        return "Chat messages not available."

    return str(data.chat_history[-1].get("output", ""))
