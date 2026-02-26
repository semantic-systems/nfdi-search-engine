from flask import (
    render_template,
    current_app,
    request,
    session,
    send_from_directory,
)

from nfdi_search_engine.extensions import limiter
from nfdi_search_engine.web.public import bp
from nfdi_search_engine.web import decorators


@bp.route("/robots.txt")
def robots():
    return send_from_directory(current_app.static_folder, "robots.txt", mimetype="text/plain")


@bp.route("/")
@limiter.limit("10 per minute")
@decorators.set_cookies
def index():
    session["back-url"] = request.url

    sources = []
    for module in current_app.config["DATA_SOURCES"]:
        sources.append(
            current_app.config["DATA_SOURCES"][module].get("logo", {}))
    # remove duplicates
    sources = [dict(t) for t in {tuple(d.items()) for d in sources}]
    template_response = render_template("index.html", sources=sources)

    return template_response
