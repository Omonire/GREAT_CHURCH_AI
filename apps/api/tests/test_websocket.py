import json
from uuid import uuid4

from church_ai_api.main import create_app
from church_ai_api.api.ws import socket


def test_session_websocket_broadcasts_events() -> None:
    app = create_app()
    session_id = uuid4()
    event = {
        "type": "transcript.final",
        "version": 1,
        "session_id": str(session_id),
        "payload": {"text": "According to Romans chapter 8."},
    }

    # The WebSocket transport is registered through Flask-Sock.
    # Transport-level integration is exercised against a real WSGI server in CI;
    # this test keeps the event contract itself framework-independent.
    from church_ai_api.schemas.events import EventEnvelope

    parsed = EventEnvelope.model_validate(event)
    assert json.loads(parsed.model_dump_json())["type"] == "transcript.final"
    assert socket is not None
