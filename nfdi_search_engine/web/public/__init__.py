from flask import Blueprint

bp = Blueprint("public", __name__)

from . import routes
