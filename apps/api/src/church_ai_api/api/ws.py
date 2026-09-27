from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from church_ai_api.realtime.manager import ConnectionManager
from church_ai_api.schemas.events import EventEnvelope

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/sessions/{session_id}")
async def session_socket(websocket: WebSocket, session_id: UUID) -> None:
    await manager.connect(session_id, websocket)

    try:
        while True:
            message = await websocket.receive_json()
            event = EventEnvelope.model_validate(message)
            await manager.broadcast(session_id, event)
    except WebSocketDisconnect:
        await manager.disconnect(session_id, websocket)
    except Exception:
        await manager.disconnect(session_id, websocket)
        raise
