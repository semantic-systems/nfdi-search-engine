from flask import Blueprint

bp = Blueprint("tracking", __name__)

from . import routes
