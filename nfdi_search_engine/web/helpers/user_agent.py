# nfdi_search_engine/web/helpers/user_agent.py
from __future__ import annotations

from dataclasses import asdict

from flask import Request
from ua_parser import user_agent_parser

from nfdi_search_engine.common.request_meta import RequestMeta


def build_user_agent_doc(request: Request, request_meta: RequestMeta) -> dict:
    """
    Build the user-agent tracking payload from Flask request + RequestMeta.
    """
    meta = asdict(request_meta)

    user_agent_string = request.headers.get("user-agent", "") or ""
    parsed = user_agent_parser.Parse(user_agent_string)

    return {
        # identity/session/request context
        "user_email": meta.get("user_email", ""),
        "session_id": meta.get("session_id", ""),
        "visitor_id": meta.get("visitor_id", ""),
        "ip_address": meta.get("client_ip", ""),
        "url": meta.get("url", ""),
        # UA details
        "user_agent": user_agent_string,
        "device_family": parsed.get("device", {}).get("family", ""),
        "device_brand": parsed.get("device", {}).get("major", ""),
        "device_model": parsed.get("device", {}).get("minor", ""),
        "os_family": parsed.get("os", {}).get("family", ""),
        "os_major": parsed.get("os", {}).get("major", ""),
        "os_minor": parsed.get("os", {}).get("minor", ""),
        "os_patch": parsed.get("os", {}).get("patch", ""),
        "os_patch_minor": parsed.get("os", {}).get("patch_minor", ""),
        "user_agent_family": parsed.get("user_agent", {}).get("family", ""),
        "user_agent_major": parsed.get("user_agent", {}).get("major", ""),
        "user_agent_minor": parsed.get("user_agent", {}).get("minor", ""),
        "user_agent_patch": parsed.get("user_agent", {}).get("patch", ""),
        "user_agent_language": getattr(request.user_agent, "language", None),
    }
