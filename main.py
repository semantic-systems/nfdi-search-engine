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
from objects import Article

import utils

from nfdi_search_engine.extensions import limiter, login_manager
from app import create_app

app = create_app()
logger = app.extensions["logger"]
utils.log_event(message="TEST")

from typing import Optional

# region ROUTES


@app.route(
    "/resource-details/<string:source_name>/<string:source_id>/<string:doi>/<string:ts>",
    methods=["GET"],
)
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

    # search for the resource in only the source_name platform
    try:
        module_name = app.config["DATA_SOURCES"][source_name].get("module", "")
        resource = importlib.import_module(f"sources.{module_name}").get_resource(
            source_name, source_id, doi
        )
    except Exception as ex:
        utils.log_event(
            type="error",
            message=(
                "resource_details - failed to load resource: "
                f"source_name={source_name}, source_id={source_id}, doi={doi}, "
                f"error={str(ex)}"
            ),
        )
        return redirect(url_for("public.index"))

    if resource is None:
        utils.log_event(
            type="error",
            message=(
                "resource_details - get_resource returned None: "
                f"source_name={source_name}, source_id={source_id}, doi={doi}"
            ),
        )
        return redirect(url_for("public.index"))

    response = make_response(
        render_template("resource-details.html", resource=resource)
    )

    return response


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
