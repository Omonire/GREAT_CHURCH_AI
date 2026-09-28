"""Health endpoints.

``/health`` stays byte-for-byte compatible with the original foundation test
(``{"status": "ok"}``) so existing checks keep passing. ``/api/health`` is the
richer version the frontend uses to decide which features are available.
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from church_ai_api import __version__
from church_ai_api.config import get_settings

blueprint = Blueprint("health", __name__)


@blueprint.get("/health")
def health():
    return jsonify(status="ok")


@blueprint.get("/api/health")
def api_health():
    settings = get_settings()
    return jsonify(
        status="ok",
        service="great-church-ai",
        version=__version__,
        environment=settings.app_env,
        features={
            "scripture": True,
            "ai_browser": True,
            "ai_server": settings.server_side_ai_enabled,
        },
    )
