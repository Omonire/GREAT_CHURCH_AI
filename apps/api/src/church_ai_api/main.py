"""Application factory.

Everything the app needs is wired here: configuration, blueprints, error
handlers, security headers, and the optional realtime transport.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, send_from_directory

from church_ai_api import __version__
from church_ai_api.api import register_blueprints
from church_ai_api.config import Settings, get_settings
from church_ai_api.utils.errors import register_error_handlers
from church_ai_api.utils.security import register_cors, register_security, split_cors

logger = logging.getLogger(__name__)


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )


def resolve_web_root(settings: Settings) -> Path | None:
    """Locate the static frontend.

    Checks the configured path, then a few sensible layouts, so the app runs
    from the repository root, from ``apps/api``, and from a container.
    """
    candidates = [
        Path(settings.web_dist),
        Path(__file__).resolve().parents[3] / "web",
        Path(__file__).resolve().parents[2] / "web",
        Path.cwd() / "web",
        Path.cwd() / "apps" / "web",
    ]
    for candidate in candidates:
        try:
            if candidate.is_dir():
                return candidate.resolve()
        except OSError:
            continue
    logger.warning("Static frontend not found; API-only mode.")
    return None


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or get_settings()
    configure_logging(settings)

    app = Flask(__name__, static_folder=None)
    app.config.update(
        JSON_SORT_KEYS=False,
        SECRET_KEY=settings.secret_key,
        IS_PRODUCTION=settings.is_production,
        TRUST_PROXY=_truthy(os.environ.get("TRUST_PROXY")),
        TRUSTED_PROXY_HOPS=_int_env("TRUSTED_PROXY_HOPS", 1),
        CORS_ORIGINS=split_cors(settings.cors_origins),
        AI_MAX_HISTORY=settings.ai_max_history,
        APP_VERSION=__version__,
    )
    app.debug = not settings.is_production and _truthy(
        os.environ.get("FLASK_DEBUG")
    )

    # A production deployment must not fall back to the development secret.
    if settings.is_production and settings.secret_key == "dev-only-insecure-key":
        logger.warning(
            "SECRET_KEY is still the development default. Set SECRET_KEY in the "
            "environment before serving this publicly."
        )

    register_blueprints(app)
    register_error_handlers(app)
    register_security(app)
    register_cors(app)

    _register_frontend(app, resolve_web_root(settings))
    _register_realtime(app, settings)

    @app.get("/")
    def index():
        if app.config.get("WEB_ROOT") is None:
            return (
                "Great Church AI API is running, but the static frontend was not found.",
                200,
            )
        return send_from_directory(app.config["WEB_ROOT"], "index.html")

    return app


def _register_frontend(app: Flask, web_root: Path | None) -> None:
    if web_root is None:
        app.config["WEB_ROOT"] = None
        return

    app.config["WEB_ROOT"] = web_root
    logger.info("Serving frontend from %s", web_root)

    @app.get("/static/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(web_root, filename)

    @app.get("/<path:filename>")
    def spa(filename: str):
        """Serve real files, otherwise fall back to a page.

        A path containing a dot is treated as a missing asset (404) rather than
        an HTML page, so a broken script never returns markup. An unknown API
        path returns a JSON 404 rather than the homepage, so a client can tell
        a missing endpoint from a missing page.
        """
        if filename.startswith("api/"):
            return _not_found()

        target = (web_root / filename).resolve()
        try:
            target.relative_to(web_root)
        except ValueError:
            return _not_found()

        if target.is_file():
            return send_from_directory(web_root, filename)
        if "." in filename:
            return _not_found()

        index = web_root / "index.html"
        if index.is_file():
            return send_from_directory(web_root, "index.html")
        return _not_found()


def _register_realtime(app: Flask, settings: Settings) -> None:
    try:
        from church_ai_api.api import ws
    except ImportError:  # pragma: no cover - optional transport
        logger.info("flask-sock unavailable; realtime transport disabled.")
        return
    ws.register(app)


def _not_found():
    from flask import jsonify

    return (
        jsonify(
            {
                "error": {
                    "code": "not_found",
                    "message": "We could not find what you were looking for.",
                    "status": 404,
                }
            }
        ),
        404,
    )


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
