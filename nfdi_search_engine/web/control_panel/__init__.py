from flask import Blueprint

bp = Blueprint("control_panel", __name__, url_prefix="/control-panel")

from . import routes
