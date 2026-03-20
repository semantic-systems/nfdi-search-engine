from __future__ import annotations

from urllib.parse import urlsplit
from dataclasses import asdict

from flask import (
    current_app,
    flash, redirect,
    render_template,
    request,
    session,
    url_for
)
from flask_login import current_user, login_required, login_user, logout_user

from nfdi_search_engine.web.auth import bp
from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.common.models.user import User
from nfdi_search_engine.services.user_service import UserService
from nfdi_search_engine.web.auth.forms import LoginForm, RegistrationForm
from nfdi_search_engine.web.auth.session_user import SessionUser


def _get_service() -> UserService:
    return current_app.extensions["services"]["users"]


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("8 per minute")
def login():
    """
    Render the login page and handle user authentication.

    :return: login page (GET/failed POST) or redirect (successful login)
    """
    if current_user.is_authenticated:
        session["current-user-email"] = current_user.email
        return redirect(session.get("back-url", url_for("public.index")))

    form = LoginForm()
    if form.validate_on_submit():
        svc = _get_service()
        user = svc.get_user_by_email(form.email.data)

        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password", "danger")
            return redirect(url_for("auth.login"))

        session_user = SessionUser(**asdict(user))
        login_user(session_user, remember=form.remember_me.data)
        session["current-user-email"] = session_user.email
        next_page = request.args.get("next")
        if not next_page or urlsplit(next_page).netloc != "":
            next_page = session.get(
                "back-url", url_for("public.index"))
        return redirect(next_page)
    return render_template("login.html", title="Login", form=form)


@bp.route("/logout")
@login_required
def logout():
    """
    Log out the current user and redirect back to the previous page.

    Clears the Flask-Login session and redirects to ``session['back-url']`` if present,
    otherwise falls back to the public index.

    :return: redirect response
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(session.get("back-url", url_for("public.index")))


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("8 per minute")
def register():
    """
    Render the registration page and handle new user creation.

    :return: registration page (GET/failed POST) or redirect to login (successful registration)
    """
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.set_password(form.password.data)

        svc = _get_service()
        svc.create_user(user)

        flash("Congratulations, you are now a registered user!", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", title="Register", form=form)
