import os
import uuid
import threading
import copy
import requests
import json
import logging
import logging.config
import secrets
from urllib.parse import urlsplit, urlencode, quote
import importlib
import hmac
from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import time
from urllib.parse import quote, unquote

from flask import (
    Flask,
    Response,
    render_template,
    request,
    make_response,
    session,
    jsonify,
    redirect,
    flash,
    url_for,
    abort,
    send_from_directory,
    abort,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user,
    login_required,
)
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from chatbot import chatbot
from objects import Article

import utils

from nfdi_search_engine.extensions import limiter, login_manager
from app import create_app

app = create_app()
logger = app.extensions["logger"]
utils.log_event(message="TEST")
# region MODELS

from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic.dataclasses import dataclass
from dataclasses import fields, field
from flask_login import UserMixin
from nfdi_search_engine.infra.result_store import InMemoryTTLResultStore
from nfdi_search_engine.infra.jobs.inprocess import InProcessDispatcher
from nfdi_search_engine.services.user_service import UserService
from nfdi_search_engine.services.search_service import SearchService, SearchSettings, ChatbotSettings
from nfdi_search_engine.services.tracking_service import TrackingService
from nfdi_search_engine.services.analytics_service import AnalyticsService
from nfdi_search_engine.services.tracking_task_proc import TrackingTaskProcessor
from nfdi_search_engine.web import decorators
from nfdi_search_engine.common import user

# ...
@dataclass
class User(UserMixin):
    id: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    password_hash: str = ""
    oauth_source: str = "self"
    included_data_sources: str = ""
    excluded_data_sources: str = ""

    def __str__(self):
        return "{} {}".format(self.first_name, self.last_name)

    def __repr__(self):
        return "{} {}".format(self.first_name, self.last_name)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id

# endregion


# region FORMS

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, widgets
from wtforms.validators import (
    ValidationError,
    DataRequired,
    Email,
    EqualTo,
    StopValidation,
)
from wtforms.fields import SelectMultipleField


    # def validate_username(self, username):
    #     user = db.session.scalar(sa.select(User).where(
    #         User.username == username.data))
    #     if user is not None:
    #         raise ValidationError('Please use a different username.')

    # def validate_email(self, email):
    #     user = db.session.scalar(sa.select(User).where(
    #         User.email == email.data))
    #     if user is not None:
    #         raise ValidationError('Please use a different email address.')


class ProfileForm(FlaskForm):
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    email = StringField(
        "Email",
        render_kw={"disabled": "disabled"},
    )
    submit = SubmitField("Save")


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(html_tag="ol", prefix_label=False)
    option_widget = widgets.CheckboxInput()


class MultiCheckboxAtLeastOne:
    def __init__(self, message=None):
        if not message:
            message = "At least one option must be selected."
        self.message = message

    def __call__(self, form, field):
        if len(field.data) == 0:
            raise StopValidation(self.message)


class PreferencesForm(FlaskForm):
    data_sources = MultiCheckboxField(
        "Data Sources", validators=[MultiCheckboxAtLeastOne()], coerce=str
    )
    submit = SubmitField("Save")


# endregion

# region ROUTES

@app.route("/profile", methods=["GET", "POST"])
@limiter.limit("10 per minute")
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        # current_user.email = form.email.data
        utils.update_user(current_user)
        flash("Your changes have been saved.", "success")
        return redirect(url_for("profile"))
    elif request.method == "GET":
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template(
        "profile.html",
        title="Profile",
        form=form,
        back_url=session.get("back-url", url_for("public.index")),
    )


@app.route("/preferences", methods=["GET", "POST"])
@limiter.limit("10 per minute")
@login_required
def preferences():
    form = PreferencesForm()
    # populate the forms dynamically with the values in the configuration and database
    data_sources_list = app.config["DATA_SOURCES"]
    form.data_sources.choices = sorted(
        [(source, source) for source in app.config["DATA_SOURCES"].keys()]
    )
    # if it's a post request and we validated successfully
    if request.method == "POST" and form.validate_on_submit():
        # get our choices again, could technically cache these in a list if we wanted but w/e
        all_sources = app.config["DATA_SOURCES"].keys()
        # need a list to hold the selections
        included_data_sources = []
        excluded_data_sources = []
        # looping through the choices, we check the choice ID against what was passed in the form
        for source in all_sources:
            # when we find a match, we then append the Choice object to our list
            if source in form.data_sources.data:
                included_data_sources.append(source)
            else:
                excluded_data_sources.append(source)
        # now all we have to do is update the users choices records
        current_user.included_data_sources = "; ".join(included_data_sources)
        current_user.excluded_data_sources = "; ".join(excluded_data_sources)
        utils.update_user_preferences_data_sources(current_user)
        flash("Your preferences have been saved.", "success")
    else:
        # tell the form what's already selected
        form.data_sources.data = [
            source for source in current_user.included_data_sources.split("; ")
        ]
    return render_template(
        "preferences.html",
        title="Preferences",
        form=form,
        back_url=session.get("back-url", url_for("public.index")),
    )


@app.route("/update-visitor-id", methods=["GET"])
@utils.timeit
def update_visitor_id():
    visitor_id = request.args.get("visitor_id")
    print(f"{visitor_id=}")
    utils.update_visitor_id(visitor_id)
    return str(True)


@app.route("/are-embeddings-generated", methods=["GET"])
@utils.timeit
def are_embeddings_generated():
    # Check the embeddings readiness only if the chatbot feature is enabled otherwise return False
    if app.config["CHATBOT"]["chatbot_enable"]:
        print("are_embeddings_generated")
        uuid = session["search_uuid"]
        chatbot_server = app.config["CHATBOT"]["chatbot_server"]
        are_embeddings_generated = app.config["CHATBOT"][
            "endpoint_are_embeddings_generated"
        ]
        request_url = f"{chatbot_server}{are_embeddings_generated}/{uuid}"
        headers = {"Content-Type": "application/json"}
        response = requests.request("GET", request_url, headers=headers)
        json_response = response.json()
        print("json_response:", json_response)
        return str(json_response["file_exists"])
    else:
        return str(True)


@app.route("/get-chatbot-answer", methods=["GET"])
@utils.timeit
def get_chatbot_answer():
    question = request.args.get("question")
    utils.log_activity(f"User asked the chatbot: {question}")
    search_uuid = session["search_uuid"]
    answer = chatbot.getAnswer(app=app, question=question, search_uuid=search_uuid)

    return answer


@app.route("/publication-details/get-dois-references/<path:doi>", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_dois_references(doi):
    """
    Endpoint to get a list of references for a given DOI.
    Uses the .get_dois_references() method from the modules.
    """

    # uses get_dois_references() from these sources:
    references_sources = {
        "CROSSREF - Publications": "crossref_publications",
        "OpenCitations": "opencitations",
    }

    found_dois = set()

    for source, module_name in references_sources.items():
        # request reference data from these endpoints
        dois = importlib.import_module(f"sources.{module_name}").get_dois_references(
            source=source, doi=doi
        )
        dois = [d.lower() for d in dois]  # ensure DOIs are lowercase

        print(f"found {len(dois)} DOIs in {source} for {doi}")

        found_dois.update(dois)

    return jsonify({"dois": list(found_dois)})


@app.route("/publication-details/get-dois-citations/<path:doi>", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_citations_dois(doi):
    """
    Endpoint to get a list of citations for a given DOI.
    Uses the .get_dois_citations() method from the modules.
    """

    # uses get_dois_citations() from these sources:
    citation_sources = {
        "SEMANTIC SCHOLAR - Publications": "semanticscholar_publications",
        "OpenCitations": "opencitations",
    }

    found_dois = set()

    for source, module_name in citation_sources.items():
        # request citation data from these endpoints
        dois = importlib.import_module(f"sources.{module_name}").get_dois_citations(
            source=source, doi=doi
        )
        dois = [d.lower() for d in dois]  # ensure DOIs are lowercase

        print(f"found {len(dois)} DOIs in {source} for {doi}")

        found_dois.update(dois)

    return jsonify({"dois": list(found_dois)})


@app.route("/publication-details/get-metadata/", methods=["POST"])
@limiter.limit("10 per minute")
def get_publication_metadata():
    """
    Endpoint to get metadata for a list of DOIs.
    Uses the .get_publication_metadata() method from the modules.
    """

    # add more metadata sources here
    # uses get_publication_metadata() from their modules
    metadata_sources = {
        "OpenCitations": "opencitations",
    }

    dois = request.json.get("dois", [])
    print(f"Received {len(dois)} DOIs for metadata retrieval")

    if not dois:
        return jsonify({"error": "No DOIs provided"}), 400

    # collect articles keyed by DOI
    collected: dict[str, Article] = {}

    for module_name in metadata_sources.values():
        articles = importlib.import_module(f"sources.{module_name}").get_batch_articles(
            dois=dois
        )

        # get all lowercase titles and DOIs from the collected articles
        list_title = [article.name.lower() for article in collected.values()]
        list_doi = [article.identifier.lower() for article in collected.values()]

        for article in articles:
            # deduplicate and add to publication_list
            # check if the article title or DOI already exists
            if (
                article.name.lower() not in list_title
                and article.identifier.lower() not in list_doi
            ):
                # article does not already exist, add it
                doi = article.identifier.lower()
                if doi and doi not in collected:
                    collected[doi] = article

    # create stub for every unresolved DOI
    for doi in dois:
        if doi not in collected:
            stub = Article(
                identifier=doi, partiallyLoaded=True
            )  # an Article with only a DOI, set flag partiallyLoaded=True
            collected[doi.lower()] = stub

    # serialize all Article objects to json
    payload = [
        art.model_dump(mode="python", exclude_none=True) for art in collected.values()
    ]

    return jsonify({"publications": payload})


@app.route(
    "/publication-details/<string:source_name>/<string:source_id>/<string:doi>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@utils.timeit
@utils.set_cookies
def publication_details(source_name, source_id, doi, ts):
    utils.log_activity(f"loading publication details page: {doi}/{source_id}")

    source_name = unquote(source_name.split(":", 1)[1])
    source_id = unquote(source_id.split(":", 1)[1])
    doi = unquote(doi.split(":", 1)[1])
    ts = unquote(ts.split(":", 1)[1])

    print(f"{doi=}")
    print(f"{source_id=}")
    print(f"{ts=}")

    try:
        timestamp_signature = ts.encode("utf-8") + b"=" * (4 - len(ts) % 4)
        timestamp_signature = base64.urlsafe_b64decode(timestamp_signature).decode(
            "utf-8"
        )
        print(f"{timestamp_signature=}")

        diff = int(time.time()) - int(float(timestamp_signature))
        print(f"{diff=}")

        if diff > 3600:
            abort(404)
    except Exception as ex:
        abort(404)

    publications = []
    sources = []
    excluded_sources = set()

    if not current_user.is_anonymous:
        excluded_sources = set((current_user.excluded_data_sources or "").split('; '))

    # Load all the sources from config.py used to harvest data related to search term
    for module in app.config["DATA_SOURCES"]:
        if (
            app.config["DATA_SOURCES"][module]
            .get("get-publication-endpoint", "")
            .strip() != ""
            and module not in excluded_sources
        ):
            sources.append(module)

    def get_publication(source, module_name, doi, source_id) -> tuple[Optional[list], Optional[Exception]]:
        mod = importlib.import_module(f"sources.{module_name}")
        partial = []

        try:
            mod.get_publication(source, doi, source_id, partial)
            return partial, None
        except Exception as e:
            return None, e

    max_workers = min(16, len(sources) or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(
                get_publication, 
                source, 
                app.config["DATA_SOURCES"][source]["module"], 
                doi, 
                source_id
            ): source
            for source in sources
        }
        for fut in as_completed(futures):
            source = futures[fut]
            partial, err = fut.result()
            if err:
                logger.warning("Source failed: %s: %s", source, err)
                continue

            publications.extend(partial)

    print(f"Total number of publications {len(publications)}")

    if len(publications) == 0:
        # none of our sources found anything about the publication!
        # show a dummy page for the user
        response = make_response(
            render_template("no-results.html", type="publication", identifier=doi)
        )

    if (
        len(publications) == 1
    ):  # forward the only publication record received from one of the sources
        response = make_response(
            render_template("publication-details.html", publication=publications[0])
        )

    else:
        # we have multiple publications
        # we merge their fields into one publication object
        merged_publication = merge_objects(publications, "publications")
        response = make_response(
            render_template("publication-details.html", publication=merged_publication)
        )

    return response


@app.route("/disabled/publication-details-references/<path:doi>", methods=["GET"])
@utils.timeit
def publication_details_references(doi):
    print("doi:", doi)

    source = "CROSSREF - Publications"
    module_name = "crossref_publications"

    reference_sources = {
        "CROSSREF - Publications": "crossref_publications",
        "OpenCitations": "opencitations",
    }

    references = []

    # this will be the base article to which we will add references
    base_article = ""

    for source, module_name in reference_sources.items():
        print(f"requesting references from {source} for DOI: {doi}")
        # request reference data from these endpoints
        article = importlib.import_module(
            f"sources.{module_name}"
        ).get_publication_references(source=source, doi=doi)

        found_references = article.references if hasattr(article, "references") else []

        # add all references whose doi is not already in the references list
        doi_list = [ref.identifier for ref in references]
        name_list = [ref.name.lower() for ref in references]
        for ref in found_references:
            if ref.identifier not in doi_list and ref.name.lower() not in name_list:
                references.append(ref)

        # change this to select another base article
        if source == "CROSSREF - Publications":
            base_article = article

    # set all references to the base article
    base_article.references = references
    response = make_response(
        render_template(
            "partials/publication-details/references.html", publication=base_article
        )
    )

    return response


@app.route("/publication-details-citations/<path:doi>", methods=["GET"])
@utils.timeit
def publication_details_citations(doi):
    print("for citations - DOI:", doi)

    # request citation data from these endpoints
    # source: module_name
    citation_sources = {
        "SEMANTIC SCHOLAR - Publications": "semanticscholar_publications",
        "OpenCitations": "opencitations",
    }

    publications = []

    for source, module_name in citation_sources.items():
        found_publications = importlib.import_module(
            f"sources.{module_name}"
        ).get_citations_for_publication(source=source, doi=doi)

        # add all publications whose doi is not already in the publications list
        doi_list = [pub.identifier for pub in publications]
        name_list = [pub.name.lower() for pub in publications]

        for pub in found_publications:
            if pub.identifier not in doi_list and pub.name.lower() not in name_list:
                publications.append(pub)

    response = make_response(
        render_template(
            "partials/publication-details/citations.html", publications=publications
        )
    )
    # print("response:", response)
    return response


@app.route("/publication-details-recommendations/<path:doi>", methods=["GET"])
@utils.timeit
def publication_details_recommendations(doi):
    print("for recommendations - DOI:", doi)
    source = "SEMANTIC SCHOLAR - Publications"
    module_name = "semanticscholar_publications"
    publications = importlib.import_module(
        f"sources.{module_name}"
    ).get_recommendations_for_publication(source=source, doi=doi)
    response = make_response(
        render_template(
            "partials/publication-details/recommendations.html",
            publications=publications,
        )
    )
    # print("response:", response)
    return response


@app.get("/publication-details/citation/format")
@limiter.limit("10 per minute")
def get_citation():
    """
    Get the citation string of a given DOI from the DOI Citation Formatter (https://citation.doi.org/).
    Query: ?doi=<doi>&style=<style>   (lang is fixed to en-US)
    Returns: { doi, style, citation }
    """

    # get the parameters for the request
    doi = (request.args.get("doi") or "").strip().lower()
    style = (request.args.get("style") or "ieee").strip()

    if not doi:
        return jsonify({"error": "missing doi"}), 400

    try:
        # send the request to citation.doi.org
        r = requests.get(
            "https://citation.doi.org/format",
            params={"doi": doi, "style": style, "lang": "en-US"},
            headers={"Accept": "text/plain; charset=utf-8"},
            timeout=10,
        )
        r.raise_for_status()
        return jsonify({"doi": doi, "style": style, "citation": r.text.strip()}), 200
    except requests.RequestException as e:
        return jsonify({"error": "citation service failed", "detail": str(e)}), 502


@app.route(
    "/researcher-details/<string:source_name>/<string:source_id>/<string:orcid>/<string:ts>",
    methods=["GET"],
)
@limiter.limit("10 per minute")
@utils.timeit
@utils.set_cookies
def researcher_details(source_name, source_id, orcid, ts):
    utils.log_activity(f"loading researcher details page: {orcid}/{source_id}")

    source_name = unquote(source_name.split(":", 1)[1])
    source_id = unquote(source_id.split(":", 1)[1])
    orcid = unquote(orcid.split(":", 1)[1])
    ts = unquote(ts.split(":", 1)[1])

    print(f"{source_name=}")
    print(f"{source_id=}")
    print(f"{orcid=}")
    print(f"{ts=}")

    try:
        timestamp_signature = ts.encode("utf-8") + b"=" * (4 - len(ts) % 4)
        timestamp_signature = base64.urlsafe_b64decode(timestamp_signature).decode(
            "utf-8"
        )
        print(f"{timestamp_signature=}")

        diff = int(time.time()) - int(float(timestamp_signature))
        print(f"{diff=}")

        if diff > 3600:
            abort(404)
    except Exception as ex:
        abort(404)

    researchers = []
    sources = []
    excluded_sources = set()

    if not current_user.is_anonymous:
        excluded_sources = set((current_user.excluded_data_sources or "").split('; '))

    # Load all the sources from config.py used to harvest data related to search term
    for module in app.config["DATA_SOURCES"]:
        if (
            app.config["DATA_SOURCES"][module]
            .get("get-researcher-endpoint", "")
            .strip() != ""
            and module not in excluded_sources
        ):
            sources.append(module)

    def get_researcher(source, module_name, orcid, source_id) -> tuple[Optional[list], Optional[Exception]]:
        mod = importlib.import_module(f"sources.{module_name}")
        partial = []

        try:
            mod.get_researcher(source, orcid, source_id, partial)
            return partial, None
        except Exception as e:
            return None, e

    max_workers = min(16, len(sources) or 1)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(
                get_researcher, 
                source, 
                app.config["DATA_SOURCES"][source]["module"], 
                orcid, 
                source_id
            ): source
            for source in sources
        }
        for fut in as_completed(futures):
            source = futures[fut]
            partial, err = fut.result()
            if err:
                logger.warning("Source failed: %s: %s", source, err)
                continue

            researchers.extend(partial)

    # publications_json = jsonify(publications)
    # with open('publications.json', 'w', encoding='utf-8') as f:
    #     json.dump(jsonify(publications).json, f, ensure_ascii=False, indent=4)

    if len(researchers) == 0:
        # none of our sources found anything about the researcher!
        # show a dummy page for the user
        response = make_response(
            render_template("no-results.html", type="researcher", identifier=orcid)
        )

    elif (
        len(researchers) == 1
    ):  # forward the only publication record received from one of the sources
        response = make_response(
            render_template("researcher-details.html", researcher=researchers[0])
        )
        session["researcher:" + orcid] = researchers[0].model_dump(
            mode="python", exclude_none=True
        )

    else:
        # merge more than one researchers record into one researcher
        merged_researcher = merge_objects(researchers, "researchers")
        response = make_response(
            render_template("researcher-details.html", researcher=merged_researcher)
        )
        session["researcher:" + orcid] = merged_researcher

    return response


@app.route("/generate-researcher-about-me/<string:orcid>", methods=["GET"])
@utils.handle_exceptions
def generate_researcher_about_me(orcid):
    researcher_about_me = generate_researcher_about_me(session["researcher:" + orcid])
    return jsonify(summary=f"{researcher_about_me}")


@app.route(
    "/resource-details/<string:source_name>/<string:source_id>/<string:doi>/<string:ts>",
    methods=["GET"],
)
@utils.handle_exceptions
def resource_details(source_name, source_id, doi, ts):
    source_name = (
        unquote(source_name.split(":", 1)[1])
        if ":" in source_name
        else unquote(source_name)
    )
    source_id = (
        unquote(source_id.split(":", 1)[1]) if ":" in source_id else unquote(source_id)
    )
    doi = unquote(doi.split(":", 1)[1]) if ":" in doi else unquote(doi)
    ts = unquote(ts.split(":", 1)[1]) if ":" in ts else unquote(ts)

    print(f"{source_name=}")
    print(f"{source_id=}")
    print(f"{doi=}")
    print(f"{ts=}")

    try:
        timestamp_signature = ts.encode("utf-8") + b"=" * (4 - len(ts) % 4)
        timestamp_signature = base64.urlsafe_b64decode(timestamp_signature).decode(
            "utf-8"
        )
        print(f"{timestamp_signature=}")

        diff = int(time.time()) - int(float(timestamp_signature))
        print(f"{diff=}")

        if diff > 3600:
            abort(404)
    except Exception as ex:
        abort(404)

    # search for the doi in only the source_name platform
    module_name = app.config["DATA_SOURCES"][source_name].get("module", "")
    resource = importlib.import_module(f"sources.{module_name}").get_resource(
        source_name, source_id, doi
    )

    response = make_response(
        render_template("resource-details.html", resource=resource)
    )

    return response


# @app.route('/generate-researcher-banner/<string:orcid>', methods=['GET'])
# @utils.handle_exceptions
# def generate_researcher_banner(orcid):
#     generated_banner = generate_researcher_banner(session['researcher:'+orcid])
#     if generated_banner == "":
#         import base64
#         with open('static/images/researcher-default-banner.jpg', "rb") as fh:
#             generated_banner = base64.b64encode(fh.read()).decode()
#     return jsonify(generated_banner = f'data:image/jpeg;base64,{generated_banner}')


# @app.route('/organization-details/<string:organization_id>/<string:organization_name>', methods=['GET'])
# @utils.timeit
# @utils.set_cookies
# def organization_details(organization_id, organization_name):
#     try:

#         # Create a response object
#         """ response = make_response()

#         # Set search-session cookie to the session cookie value of the first visit
#         if request.cookies.get('search-session') is None:
#             if request.cookies.get('session') is None:
#                 response.set_cookie('search-session', str(uuid.uuid4()))
#             else:
#                 response.set_cookie('search-session', request.cookies['session'])"""

#         # Call the org_details function from the gepris module to fetch organization details by id
#         organization, sub_organization, sub_project = org_details(organization_id, organization_name)

#         if organization or sub_organization or sub_project:
#             # Render the organization-details.html template
#             return render_template('organization-details.html', organization=organization,
#                                    sub_organization=sub_organization, sub_project=sub_project)
#         else:
#             # Handle the case where organization details are not found (e.g., return a 404 page)
#             return render_template('error.html', error_message='Organization details not found.')

#     except ValueError as ve:
#         return render_template('error.html', error_message=str(ve))
#     except Exception as e:
#         return render_template('error.html', error_message='An error occurred: ' + str(e))


# @app.route('/events-details')
# @utils.timeit
# @utils.set_cookies
# def events_details():
#     response = make_response(render_template('events-details.html'))

#     # Set search-session cookie to the session cookie value of the first visit
#     if request.cookies.get('search-session') is None:
#         if request.cookies.get('session') is None:
#             response.set_cookie('search-session', str(uuid.uuid4()))
#         else:
#             response.set_cookie('search-session', request.cookies['session'])

#     return response


# @app.route('/project-details')
# @utils.timeit
# @utils.set_cookies
# def project_details():
#     response = make_response(render_template('project-details.html'))
#     # Set search-session cookie to the session cookie value of the first visit
#     if request.cookies.get('search-session') is None:
#         if request.cookies.get('session') is None:
#             response.set_cookie('search-session', str(uuid.uuid4()))
#         else:
#             response.set_cookie('search-session', request.cookies['session'])

#     return response


@app.route("/digital-obj-details/<path:identifier_with_type>", methods=["GET"])
@limiter.limit("10 per minute")
@utils.timeit
@utils.set_cookies
def digital_obj_details(identifier_with_type):
    utils.log_activity(f"loading digital obj details page: {identifier_with_type}")
    identifier_type = identifier_with_type.split(":", 1)[
        0
    ]  # as of now this is hardcoded as 'doi'
    identifier = identifier_with_type.split(":", 1)[1]
    pass


for code, message in app.config["ERROR_MESSAGES"].items():

    @app.errorhandler(code)
    def handle_error(e, message=message, code=code):
        # utils.log_activity(f"{message} Exception: {e}")
        return render_template("error.html", error_message=message), code

# endregion


# region GEN AI


system_content_for_publications_merging = """
    You are given a list of digital objects. These digital objects have been duplicated multiple times in the list. 
    Your task is to consolidate these objects into a single object, ensuring that all properties or attributes of each digital object are preserved. 
    If a property or attribute has multiple values, please use your best judgement to determine the final value. 
    The consolidated output should be presented as a JSON format.

    Ensure the following:
    - No property or attribute of the digital object is missed out.
    - If multiple values exist for the same property or attribute, decide the final value based on common sense or logic.
    - The consolidated digital object should be in a valid JSON format.
    - Only the properties of the digital objects should be included in the final JSON.
    - If the final decision on any property's value is 'None', replace that with 'null' in the resulting JSON.
    - Your response should only be the consolidated digital object in JSON format, without any additional details or context.

    """


@utils.handle_exceptions
def generate_response_with_local_llm(publications_json):
    url = app.config["LLMS"]["llama3"]["url"]
    llm_username = app.config["LLMS"]["llama3"]["username"]
    llm_password = app.config["LLMS"]["llama3"]["password"]
    payload = json.dumps(
        {
            "messages": [
                {"role": "system", "content": system_content_for_publications_merging},
                {"role": "user", "content": f"{publications_json}"},
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "max_new_tokens": 16384,
            "max_seq_len": 1024,
            "max_gen_len": 512,
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request(
        "POST", url, auth=(llm_username, llm_password), headers=headers, data=payload
    )
    response_json = json.loads(response.text)
    generated_text = response_json["generated_text"]
    print(generated_text)
    merged_publication = json.loads(generated_text)
    return merged_publication


@utils.handle_exceptions
def generate_response_with_openai(publications_json):
    url = app.config["LLMS"]["openai"]["url_chat_completions"]
    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_content_for_publications_merging},
                {"role": "user", "content": f"{publications_json}"},
            ],
            "temperature": 0.7,
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    merged_publication = json.loads(
        response_json["choices"][0]["message"]["content"]
        .replace("```json", "")
        .replace("```", "")
    )
    print(merged_publication)
    return merged_publication


@utils.handle_exceptions
def generate_researcher_about_me(researcher_details_json):
    # researcher.about = chat_completion.choices[0].message.content.strip()

    url = app.config["LLMS"]["openai"]["url_chat_completions"]
    system_content = """
    Generate an introductory paragraph (4-6 sentences) for the researcher whose affiliation, publications, research interests are provided in the form of key value pairs, 
    wherein the definitions of the keys are derived from schema.org. 
    The summary should briefly describe the researcher’s current affiliation, highlight notable publications, and outline their main research interests.
    It should not include the researcher ORCID link in the generated summary.
    Generate the summary for the information provided, avoid including any external information or knowledge.

    """
    payload = json.dumps(
        {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": f"{researcher_details_json}"},
            ],
            "temperature": 0.7,
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_json = json.loads(response.text)
    response_message = response_json["choices"][0]["message"]["content"]
    print(response_message)
    return response_message


@utils.handle_exceptions
def generate_researcher_banner(researcher_details_json):
    url = app.config["LLMS"]["openai"]["url_images_generations"]
    prompt = """
    Generate an image with following instructions:
    - A researcher is either working in his desk and books on his table are related to his research areas.
    - or the researcher is reading something in the library and the books in the background are related to his research areas.
    - or the researcher is doing something on his laptop and the screen has diagrams or images related to his research areas.
    - Researcher sketch should be gender neutral.
    - Image should have linear gradient which start with dark colors on the right but fades out with very light colors on the left.
    - Research Areas: artificial intelligence, machine learning, knowledge graphs, computer vision, large language models

    """
    payload = json.dumps(
        {
            "model": "dall-e-3",
            "response_format": "b64_json",
            "quality": "standard",
            "n": 1,
            "prompt": prompt,
            # "size": "1296x193",
            # "size": "1792x1024",
            "size": "1024x1024",
            # Include any additional parameters here
        }
    )
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', '')}",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    if response.status_code == 200:
        generated_banner = response.json()["data"][0]["b64_json"]
        return generated_banner
    else:
        utils.log_event(type="error", message=f"{response.text}")
        return ""

    # details = vars(researcher)
    # details_str = "\n".join(f"{convert_to_string(value)}" for key, value in details.items() if (value not in ("", [], {}, None) and key in ("researchAreas")))
    # prompt = f"A banner for researcher with following research areas:\n{researcher.about}"
    # client = OpenAI(api_key=utils.env_config["OPENAI_API_KEY"])
    # response = client.images.generate(
    #     model="dall-e-2",
    #     prompt=prompt,
    #     size="512x512",
    #     quality="standard",
    #     response_format="b64_json",
    #     n=1,
    # )
    # researcher.banner = response.data[0].b64_json
    # return researcher


# endregion

# region MISC


@utils.handle_exceptions
def merge_objects(object_list, object_type):
    """
    This function revieces a list of objects defined in objects.py, and returns a new object with the merged values of the objects in object_list.
    The preference order for merging is defined under MAPPING_PREFERENCE in config.py.
    """

    # the new object we create will have the type of the object in object_list which is furthest down in the inheritance hierarchy
    # => we search for the obj with the longest __mro__
    target_obj = max(object_list, key=lambda x: len(type(x).__mro__))
    target_cls = type(target_obj)
    merged_object = target_cls()

    # sort object_list by mapping preference
    mapping_pref = app.config["MAPPING_PREFERENCE"].get(object_type, {})

    # this function returns the index of the source in the preference list for the field
    # it returns float('inf') if the source is not in the preference list
    def get_preference_index(obj, field_name):
        # get the name of the source of the object
        source_list = getattr(obj, "source", None)
        source = source_list[0] if source_list else None
        source_name = getattr(source, "name", None) if source else None

        # get the preference order for the field
        pref_list = mapping_pref.get(field_name, mapping_pref.get("__default__", []))

        return (
            pref_list.index(source_name) if source_name in pref_list else float("inf")
        )

    # collect all sources that will be used in the merged object
    sources = set()

    # iterate through the sorted objects and choose the first non-empty value for each field in the merged object
    for field in type(merged_object).model_fields.keys():
        # sort the objects by the current field
        # if the field is not found, the objects are sorted with the __default__ list
        sorted_objects = sorted(
            object_list, key=lambda obj: get_preference_index(obj, field)
        )

        # iterate through the sorted objects until one of them contains a non-empty value for the field
        for obj in sorted_objects:
            val = getattr(obj, field, None)

            if val not in (
                None,
                "",
                [],
                {},
            ):  # check if the value is empty or a placeholder
                setattr(merged_object, field, val)

                # add all sources to the merged object
                source_list = set(getattr(obj, "source", []))
                sources.update(source_list)

                break

    # add the sources to the merged object
    merged_object.source = list(sources)

    return merged_object


# endregion


#region IP BAN

# @app.route('/get-block-list', methods=['GET'])
# @utils.timeit
# def get_block_list():
#     utils.log_activity("get_block_list")
#     s = '<html><body>'
#     s += '<table class="table" style="width: 100%"><thead>\n'
#     s += '<tr><th>ip</th><th>count</th><th>permanent</th><th>url</th><th>timestamp</th></tr>\n'
#     s += '</thead><tbody>\n'
#     for k, r in ip_ban.get_block_list().items():
#         s += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n'.format(k, r['count'],
#                                                                                         r.get('permanent', ''),
#                                                                                         r.get('url', ''),
#                                                                                         r['timestamp'])

#     s += '</body></html>'
#     return s

# @app.route('/ip-ban-block/<string:ip_address>', methods=['GET'])
# @utils.timeit
# def ip_ban_block(ip_address):
#     utils.log_activity(f"ip_ban_block: {ip_address}")
#     ip_ban.block(ip_list=[ip_address])
#     return f"IP address {ip_address} has been blocked."

# @app.route('/ip-ban-add/<string:ip_address>', methods=['GET'])
# @utils.timeit
# def ip_ban_add(ip_address):
#     utils.log_activity(f"ip_ban_add: {ip_address}")
#     ip_ban.add(ip=ip_address)
#     return f"IP address {ip_address} has been added to the list."

# @app.route('/ip-ban-remove/<string:ip_address>', methods=['GET'])
# @utils.timeit
# def ip_ban_remove(ip_address):
#     utils.log_activity(f"ip_ban_remove: {ip_address}")
#     ip_ban.remove(ip=ip_address)
#     return f"IP address {ip_address} has been removed from the list."

# @app.route('/ip-whitelist-add/<string:ip_address>', methods=['GET'])
# @utils.timeit
# def ip_whitelist_add(ip_address):
#     utils.log_activity(f"ip_whitelist_add: {ip_address}")
#     ip_ban.ip_whitelist_add(ip=ip_address)
#     return f"IP address {ip_address} has been added to the whitelist."

# @app.route('/ip-whitelist-remove/<string:ip_address>', methods=['GET'])
# @utils.timeit
# def ip_whitelist_remove(ip_address):
#     utils.log_activity(f"ip_whitelist_remove: {ip_address}")
#     ip_ban.ip_whitelist_remove(ip=ip_address)
#     return f"IP address {ip_address} has been removed from the whitelist."

#endregion


@limiter.request_filter
def ip_whitelist():
    return request.remote_addr == "127.0.0.1"


# region Control Panel


# endregion

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
