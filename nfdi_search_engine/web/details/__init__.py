from flask import Blueprint

bp = Blueprint("details", __name__)

from . import publication_routes
