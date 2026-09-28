from __future__ import annotations

from collections import defaultdict
from threading import Lock
from uuid import UUID

from church_ai_api.schemas.events import EventEnvelope


class ConnectionManager:
    """Thread-safe registry of live websocket connections per session."""

    def __init__(self) -> None:
        self._connections: dict[UUID, set[object]] = defaultdict(set)
        self._lock = Lock()

    def connect(self, session_id: UUID, websocket: object) -> None:
        with self._lock:
            self._connections[session_id].add(websocket)

    def disconnect(self, session_id: UUID, websocket: object) -> None:
        with self._lock:
            connections = self._connections.get(session_id)
            if not connections:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(session_id, None)

    def count(self, session_id: UUID) -> int:
        with self._lock:
            return len(self._connections.get(session_id, ()))

    def broadcast_sync(
        self, session_id: UUID, event: EventEnvelope, sender: object
    ) -> None:
        self.connect(session_id, sender)
        with self._lock:
            connections = list(self._connections.get(session_id, set()))

        payload = event.model_dump_json()
        dead: list[object] = []

        for websocket in connections:
            try:
                websocket.send(payload)
            except Exception:
                dead.append(websocket)

        for websocket in dead:
            self.disconnect(session_id, websocket)
