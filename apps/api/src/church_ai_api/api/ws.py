from __future__ import annotations

import logging
from uuid import UUID

from flask import Flask
from flask_sock import Sock
from pydantic import ValidationError

from church_ai_api.realtime.manager import ConnectionManager
from church_ai_api.schemas.events import EventEnvelope

logger = logging.getLogger(__name__)

socket = Sock()
manager = ConnectionManager()


@socket.route("/ws/sessions/<session_id>")
def session_socket(ws, session_id: str) -> None:
    """Realtime session channel.

    The transport stays intentionally thin: it validates the versioned event
    envelope, then echoes the event to every connection in the session. It does
    not exist yet to drive the consumer product; it is retained because the
    roadmap keeps realtime media work in scope and it is covered by tests.
    """
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        logger.warning("Rejected websocket with malformed session id")
        try:
            ws.send(
                EventEnvelope(
                    type="system.error",
                    session_id=UUID(int=0),
                    payload={"message": "Invalid session id."},
                ).model_dump_json()
            )
        except Exception:
            pass
        return

    try:
        while True:
            message = ws.receive()
            if message is None:
                break

            try:
                event = EventEnvelope.model_validate_json(message)
            except ValidationError as error:
                logger.warning("Rejected malformed realtime event: %s", error.error_count())
                ws.send(
                    EventEnvelope(
                        type="system.error",
                        session_id=session_uuid,
                        payload={"message": "Malformed event envelope."},
                    ).model_dump_json()
                )
                continue

            manager.broadcast_sync(session_uuid, event, ws)
    except Exception:  # pragma: no cover - transport teardown
        logger.info("Websocket session %s closed", session_uuid)
    finally:
        manager.disconnect(session_uuid, ws)


def register(app: Flask) -> None:
    socket.init_app(app)
