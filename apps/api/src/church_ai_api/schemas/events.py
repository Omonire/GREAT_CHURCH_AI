from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


EventType = Literal[
    "transcript.partial",
    "transcript.final",
    "scripture.detected",
    "context.updated",
    "media.suggestion.created",
    "media.suggestion.updated",
    "media.action.approved",
    "media.action.rejected",
    "system.error",
]


class EventEnvelope(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: EventType
    version: int = 1
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    session_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
