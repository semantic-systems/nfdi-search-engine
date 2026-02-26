from __future__ import annotations

from flask_limiter import Limiter
from flask_login import LoginManager
from flask_session import Session

from nfdi_search_engine.web.helpers.ip import get_client_ip

limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["500 per day", "120 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)

session_ext = Session()
login_manager = LoginManager()
