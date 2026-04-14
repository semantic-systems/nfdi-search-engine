from __future__ import annotations

from flask import Flask, render_template


def register_error_handlers(app: Flask) -> None:
    """
    Register configured error handlers from app.config["ERROR_MESSAGES"].
    """

    error_messages = app.config.get("ERROR_MESSAGES", {}) or {}

    for code, message in error_messages.items():
        # define a handler function for this code
        def handler(e, message=message, code=code):
            return render_template("error.html", error_message=message), code

        app.register_error_handler(code, handler)
