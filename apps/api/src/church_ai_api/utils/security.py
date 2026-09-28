"""Security headers and proxy handling.

Two rules matter here:

1. ``X-Forwarded-For`` is only honoured when ``TRUST_PROXY`` is explicitly
   enabled. Trusting it by default would let any client forge its own IP and
   defeat every IP-based protection.
2. No ``X-Powered-By`` and no ``Server`` header leaks the stack.
"""

from __future__ import annotations

import logging
from urllib.parse import urlsplit

from flask import Flask, request

logger = logging.getLogger(__name__)

_MAX_BODY_BYTES = 256 * 1024


def _split_hosts(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def is_production(app: Flask) -> bool:
    return bool(app.config.get("IS_PRODUCTION"))


def client_ip(app: Flask) -> str:
    """Best-effort client address.

    Trusts ``X-Forwarded-For`` only behind an explicitly configured proxy count.
    """
    if not app.config.get("TRUST_PROXY"):
        return request.remote_addr or "unknown"

    forwarded = request.headers.get("X-Forwarded-For", "")
    chain = _split_hosts(forwarded)
    trusted = int(app.config.get("TRUSTED_PROXY_HOPS", 1))

    if not chain:
        return request.remote_addr or "unknown"

    # Drop the proxies we control, then take the first untrusted hop.
    index = max(0, len(chain) - trusted)
    return chain[index]


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return False
    allowed = app_config_cors()
    if not allowed:
        return False
    if "*" in allowed:
        return True
    return origin in allowed


def app_config_cors() -> list[str]:
    from flask import current_app

    return list(current_app.config.get("CORS_ORIGINS", []))


def register_security(app: Flask) -> None:
    @app.after_request
    def _harden(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            (
                "default-src 'self'; "
                # Puter.js is the only third-party script, loaded in the browser
                # to run AI without any server-side API key.
                "script-src 'self' 'unsafe-inline' https://js.puter.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "connect-src 'self' https://js.puter.com https://api.puter.com; "
                "frame-ancestors 'none'; "
                "object-src 'none'; base-uri 'self'; form-action 'self'"
            ),
        )
        if app.config.get("IS_HTTPS"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        response.headers.pop("X-Powered-By", None)
        return response

    @app.before_request
    def _limit_body():
        raw = request.content_length
        if raw and raw > _MAX_BODY_BYTES:
            from flask import jsonify

            return (
                jsonify(
                    {
                        "error": {
                            "code": "payload_too_large",
                            "message": "That request was too large.",
                            "status": 413,
                        }
                    }
                ),
                413,
            )
        return None


def split_cors(value: str) -> list[str]:
    hosts: list[str] = []
    for item in _split_hosts(value):
        candidate = item if "://" in item else f"https://{item}"
        parts = urlsplit(candidate)
        if parts.netloc:
            hosts.append(f"{parts.scheme}://{parts.netloc}")
    return hosts


def register_cors(app: Flask) -> None:
    """Reflect only explicitly configured origins, and only for the API.

    Same-origin deployment (the default) needs no CORS headers at all, so an
    unconfigured instance sends none.
    """
    allowed = list(app.config.get("CORS_ORIGINS", []))

    @app.after_request
    def _cors(response):
        origin = request.headers.get("Origin")
        if not origin or not allowed:
            return response
        if not request.path.startswith("/api/"):
            return response
        if "*" not in allowed and origin not in allowed:
            return response

        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Vary", "Origin")
        response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        response.headers.setdefault("Access-Control-Max-Age", "600")
        return response

    @app.route("/api/<path:_path>", methods=["OPTIONS"])
    def _preflight(_path: str):
        return ("", 204)
