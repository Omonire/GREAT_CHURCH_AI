from uuid import uuid4

from church_ai_api.schemas.events import EventEnvelope


def test_event_envelope_defaults() -> None:
    event = EventEnvelope(type="transcript.final", session_id=uuid4())
    assert event.version == 1
    assert event.payload == {}
