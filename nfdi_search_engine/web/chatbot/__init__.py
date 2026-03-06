from flask import Blueprint

bp = Blueprint("chatbot", __name__)

from . import routes
