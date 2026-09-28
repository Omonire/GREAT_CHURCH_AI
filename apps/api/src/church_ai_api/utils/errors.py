"""Shared error handling and JSON error shape.

Every failure the user can trigger returns JSON with a stable shape::

    {"error": {"code": "scripture_unavailable", "message": "..."}}

Production responses never include a traceback or any internal detail.
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def _payload(code: str, message: str, status: int, **extra):
    body = {"error": {"code": code, "message": message, "status": status}}
    body["error"].update({k: v for k, v in extra.items() if v is not None})
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def _validation(error: ValidationError):
        fields = sorted({str(item["loc"][-1]) for item in error.errors() if item.get("loc")})
        detail = f" Check: {', '.join(fields)}." if fields else ""
        return _payload(
            "invalid_request",
            "Some of the information we received was not valid." + detail,
            400,
            fields=fields or None,
        )

    @app.errorhandler(400)
    def _bad_request(error: HTTPException):
        return _payload("bad_request", "That request was not valid.", 400)

    @app.errorhandler(404)
    def _not_found(error: HTTPException):
        return _payload("not_found", "We could not find what you were looking for.", 404)

    @app.errorhandler(405)
    def _not_allowed(error: HTTPException):
        return _payload(
            "method_not_allowed", "That action is not available for this address.", 405
        )

    @app.errorhandler(413)
    def _too_large(error: HTTPException):
        return _payload("payload_too_large", "That request was too large.", 413)

    @app.errorhandler(429)
    def _too_many(error: HTTPException):
        return _payload(
            "rate_limit_exceeded",
            "Too many requests. Please slow down and try again shortly.",
            429,
        )

    @app.errorhandler(Exception)
    def _unexpected(error: Exception):
        # Log the detail server-side, tell the user nothing about it.
        logger.exception("Unhandled server error: %s", type(error).__name__)
        if app.debug:
            return _payload("server_error", str(error), 500)
        return _payload(
            "server_error",
            "Something went wrong while preparing your response. Please try again.",
            500,
        )
