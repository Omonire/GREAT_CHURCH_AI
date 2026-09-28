"""WSGI entry point for production servers.

Gunicorn, uWSGI, and most hosts expect a module that exposes a plain ``app``
object, for example::

    gunicorn church_ai_api.wsgi:app --bind 0.0.0.0:$PORT

A factory target such as ``church_ai_api.main:create_app()`` also works, but
the parentheses have to survive the host's shell. Render passes the start
command through ``bash -c``, where an unquoted ``create_app()`` is a syntax
error. Keeping the target free of shell metacharacters avoids that trap and
gives every host the same entry point.
"""

from __future__ import annotations

from church_ai_api.main import create_app

# Settings are read once, here, at import time. Hosts treat import of this
# module as process start, so each worker reads the environment exactly once.
app = create_app()
