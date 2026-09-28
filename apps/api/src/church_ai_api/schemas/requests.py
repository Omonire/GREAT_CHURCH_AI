"""Request and response models for the JSON API.

Validation lives here so blueprints stay thin and every endpoint rejects bad
input the same way.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 4000
MAX_DETAIL_LENGTH = 600


def _clean(value: str) -> str:
    return " ".join(value.split())


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("content")
    @classmethod
    def _normalise(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[ChatMessage] = Field(default_factory=list, max_length=24)
    reference: str | None = Field(default=None, max_length=80)

    @field_validator("message")
    @classmethod
    def _normalise_message(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned

    @field_validator("reference")
    @classmethod
    def _clean_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class StudyRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=32)
    include_scripture: bool = True

    @field_validator("reference", "action")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class PrayerRequest(BaseModel):
    topic: str = Field(default="gratitude", min_length=1, max_length=40)
    detail: str | None = Field(default=None, max_length=MAX_DETAIL_LENGTH)
    reference: str | None = Field(default=None, max_length=80)
    generate: bool = True

    @field_validator("topic")
    @classmethod
    def _clean_topic(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("detail", "reference")
    @classmethod
    def _clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class PrayerDraftRequest(BaseModel):
    """A freeform prayer request: the user describes the situation."""

    situation: str = Field(min_length=3, max_length=1000)
    reference: str | None = Field(default=None, max_length=80)

    @field_validator("situation")
    @classmethod
    def _clean_situation(cls, value: str) -> str:
        cleaned = _clean(value)
        if not cleaned:
            raise ValueError("Describe what you want to pray about.")
        return cleaned

    @field_validator("reference")
    @classmethod
    def _clean_draft_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=120)
    limit: int = Field(default=20, ge=1, le=50)


class OutlineRequest(BaseModel):
    """A preaching outline request from a church leader."""

    reference: str = Field(min_length=1, max_length=80)
    title: str | None = Field(default=None, max_length=160)
    body: str | None = Field(default=None, max_length=4000)

    @field_validator("reference")
    @classmethod
    def _strip_reference(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("A passage is required.")
        return cleaned

    @field_validator("title", "body")
    @classmethod
    def _clean_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
