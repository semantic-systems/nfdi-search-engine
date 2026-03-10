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
