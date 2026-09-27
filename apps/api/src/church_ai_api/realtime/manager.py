import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[session_id].add(websocket)

    async def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(session_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(session_id, None)

    async def broadcast(self, session_id: UUID, event: EventEnvelope) -> None:
        connections = list(self._connections.get(session_id, set()))
        dead: list[WebSocket] = []

        for websocket in connections:
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                dead.append(websocket)

        for websocket in dead:
            await self.disconnect(session_id, websocket)
