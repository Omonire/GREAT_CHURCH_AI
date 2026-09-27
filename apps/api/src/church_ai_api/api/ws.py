from uuid import UUID

from flask_sock import Sock

from church_ai_api.realtime.manager import ConnectionManager
from church_ai_api.schemas.events import EventEnvelope

socket = Sock()
manager = ConnectionManager()


@socket.route("/ws/sessions/<session_id>")
def session_socket(ws, session_id: str) -> None:
    session_uuid = UUID(session_id)

    while True:
        message = ws.receive()
        if message is None:
            break

        event = EventEnvelope.model_validate_json(message)
        manager.broadcast_sync(session_uuid, event, ws)
