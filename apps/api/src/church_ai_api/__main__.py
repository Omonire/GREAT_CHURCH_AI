"""Development and production entrypoint.

Run locally with::

    python -m church_ai_api.main
"""

from __future__ import annotations

from church_ai_api.config import get_settings
from church_ai_api.main import create_app

settings = get_settings()

# WSGI target for gunicorn/uwsgi: church_ai_api.main:app
app = create_app(settings)


def main() -> None:
    settings = get_settings()
    # The dev server is single-process and not for production use.
    app.run(
        host=settings.api_host,
        port=settings.api_port,
        debug=app.debug,
    )


if __name__ == "__main__":
    main()
