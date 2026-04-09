from __future__ import annotations

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.account import bp
from nfdi_search_engine.web.account.forms import ProfileForm, PreferencesForm
from nfdi_search_engine.services.user_service import UserService


def _get_service() -> UserService:
    return current_app.extensions["services"]["users"]


@bp.route("/profile", methods=["GET", "POST"])
@limiter.limit("10 per minute")
@login_required
def profile():
    """
    Render and update the user profile.

    :return: profile page template (GET/invalid POST) or redirect (successful update)
    """
    form = ProfileForm()

    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data

        svc = _get_service()
        svc.update_user_profile(current_user)

        flash("Your changes have been saved.", "success")
        return redirect(url_for("account.profile"))

    if request.method == "GET":
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email

    return render_template(
        "profile.html",
        title="Profile",
        form=form,
        back_url=session.get("back-url", url_for("public.index")),
    )


@bp.route("/preferences", methods=["GET", "POST"])
# @limiter.limit("10 per minute")
@login_required
def preferences():
    """
    Render and update user data-source preferences.

    :return: preferences page template (GET/invalid POST) or redirect (successful update)
    """
    form = PreferencesForm()

    # populate the forms dynamically with the values in the configuration and database
    all_sources = list(current_app.config["DATA_SOURCES"].keys())
    form.data_sources.choices = sorted(all_sources)
    #    [(src, src) for src in all_sources]
    #)
    # if it's a post request and we validated successfully
    if request.method == "POST" and form.validate_on_submit():
        # need a list to hold the selections
        selected = set(form.data_sources.data or [])

        included = [src for src in all_sources if src in selected]
        excluded = [src for src in all_sources if src not in selected]

        # update the users preferences
        current_user.included_data_sources = "; ".join(included)
        current_user.excluded_data_sources = "; ".join(excluded)

        svc = _get_service()
        svc.update_user_preferences(current_user)
        flash("Your preferences have been saved.", "success")
        return redirect(url_for("account.preferences"))

    # for get or invalid post:
    # tell the form what's already selected
    form.data_sources.data = [
        s for s in (current_user.included_data_sources or "").split("; ") if s
    ]

    return render_template(
        "preferences.html",
        title="Preferences",
        form=form,
        back_url=session.get("back-url", url_for("public.index")),
    )
