"""Flask API blueprints."""

from __future__ import annotations

from flask import Flask

from church_ai_api.api import ai, bible, health, prayer, sermons


def register_blueprints(app: Flask) -> None:
    for module in (health, ai, bible, prayer, sermons):
        app.register_blueprint(module.blueprint)


__all__ = ["register_blueprints", "ai", "bible", "health", "prayer", "sermons"]
