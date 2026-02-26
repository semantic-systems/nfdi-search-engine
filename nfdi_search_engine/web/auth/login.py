from __future__ import annotations

from dataclasses import asdict

from flask import current_app
from nfdi_search_engine.extensions import login_manager
from nfdi_search_engine.services.user_service import UserService
from nfdi_search_engine.web.auth.session_user import SessionUser

def init_login_loader():
    @login_manager.user_loader
    def load_user(user_id: str):
        user_svc: UserService = current_app.extensions["services"]["users"]
        user = user_svc.get_user_by_id(user_id)
        return SessionUser(**asdict(user))
