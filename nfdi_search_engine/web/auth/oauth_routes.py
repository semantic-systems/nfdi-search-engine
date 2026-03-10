from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Blueprint, abort, current_app, flash, redirect, request, session, url_for
from flask_login import current_user, login_user

from nfdi_search_engine.web.auth import bp
from nfdi_search_engine.common.models.user import User


def _user_service():
    return current_app.extensions["services"]["users"]


# authization code copied from https://github.com/miguelgrinberg/flask-oauth-example
@bp.route("/authorize/<provider>")
def oauth2_authorize(provider):
    if not current_user.is_anonymous:
        return redirect(url_for("public.index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session["oauth2_state"] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode(
        {
            "client_id": provider_data["client_id"],
            "redirect_uri": url_for(
                "auth.oauth2_callback",
                provider=provider,
                _external=True,
                _scheme=os.environ.get("PREFERRED_URL_SCHEME", "https"),
            ),
            "response_type": "code",
            "scope": " ".join(provider_data["scopes"]),
            "state": session["oauth2_state"],
        }
    )

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data["authorize_url"] + "?" + qs)


@bp.route("/callback/<provider>")
def oauth2_callback(provider: str):
    if not current_user.is_anonymous:
        return redirect(url_for("public.index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    if "error" in request.args:
        for k, v in request.args.items():
            if k.startswith("error"):
                flash(f"{k}: {v}")
        return redirect(url_for("public.index"))

    if request.args.get("state") != session.get("oauth2_state"):
        abort(401)

    code = request.args.get("code")
    if not code:
        abort(401)

    token_resp = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": url_for(
                "auth.oauth2_callback",
                provider=provider,
                _external=True,
                _scheme=os.environ.get("PREFERRED_URL_SCHEME", "https"),
            ),
        },
        headers={"Accept": "application/json"},
        timeout=20,
    )
    if token_resp.status_code != 200:
        abort(401)

    oauth2_token = token_resp.json().get("access_token")
    if not oauth2_token:
        abort(401)

    userinfo_resp = requests.get(
        provider_data["userinfo"]["url"],
        headers={
            "Authorization": "Bearer " + oauth2_token,
            "Accept": "application/json",
        },
        timeout=20,
    )
    if userinfo_resp.status_code != 200:
        abort(401)

    email = provider_data["userinfo"]["email"](userinfo_resp.json())

    user_svc = _user_service()

    existing = user_svc.get_user_by_email(email)
    if existing:
        # update oauth_source if needed
        if provider != existing.oauth_source:
            existing.oauth_source = provider
            user_svc.update_user_profile(existing)
        user = existing
    else:
        # create new user (derive name from email local part)
        local = email.split("@")[0]
        nice = local.replace("-", " ").replace(".", " ").replace("_", " ")
        tokens = [t for t in nice.split(" ") if t]

        first = tokens[0] if tokens else local
        last = tokens[1] if len(tokens) > 1 else ""

        user = User(first_name=first, last_name=last, email=email, oauth_source=provider)
        # no password for OAuth-only users
        user_svc.create_user(user)

        # re-fetch to get ID (since create_user inserts without returning _id)
        user = user_svc.get_user_by_email(email) or user

    login_user(user)
    session["current-user-email"] = user.email
    return redirect(url_for("public.index"))
