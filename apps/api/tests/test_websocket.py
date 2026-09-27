from uuid import uuid4

from fastapi.testclient import TestClient

from church_ai_api.main import app


def test_session_websocket_broadcasts_events() -> None:
    session_id = uuid4()
    event = {
        "type": "transcript.final",
        "version": 1,
        "session_id": str(session_id),
        "payload": {"text": "According to Romans chapter 8."},
    }

    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/sessions/{session_id}") as websocket:
            websocket.send_json(event)
            received = websocket.receive_json()

    assert received["type"] == "transcript.final"
    assert received["session_id"] == str(session_id)
    assert received["payload"]["text"] == event["payload"]["text"]
    assert "id" in received
    assert "timestamp" in received
