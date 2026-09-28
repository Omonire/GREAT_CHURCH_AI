"""AI endpoints.

``/api/ai/chat`` and its siblings prepare a prompt. They do not call a model by
default: the browser sends the prepared prompt to Puter.js, which needs no API
key and no server credentials. If a server-side provider is configured the
response additionally carries a generated ``reply`` so the same UI works
unchanged.
"""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, jsonify, request

from church_ai_api.ai.context import HUMANITY_NOTE, ChatTurn
from church_ai_api.ai.prompts import (
    available_actions,
    detect_themes,
    prepare_chat,
    prepare_prayer,
    prepare_prayer_draft,
    prepare_study,
)
from church_ai_api.ai.provider import ProviderError, ServerProvider
from church_ai_api.ai.suggestions import STARTER_PROMPTS
from church_ai_api.bible.service import ScriptureError, get_scripture_service
from church_ai_api.schemas.requests import (
    ChatRequest,
    PrayerDraftRequest,
    PrayerRequest,
    StudyRequest,
)

logger = logging.getLogger(__name__)

blueprint = Blueprint("ai", __name__, url_prefix="/api/ai")


def _json_body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _resolve_scripture(reference: str | None) -> tuple[str | None, dict | None]:
    """Best-effort Scripture grounding. Never fails the request."""
    if not reference:
        return None, None
    try:
        passage = get_scripture_service().get_reference(reference)
    except ScriptureError as error:
        logger.info("Scripture grounding skipped for %r: %s", reference, error)
        return None, None
    return passage.get("text"), passage


def _try_server_completion(prompt) -> tuple[str | None, str | None]:
    provider = ServerProvider()
    if not provider.enabled:
        return None, None
    try:
        return provider.complete(prompt), None
    except ProviderError as error:
        logger.warning("Server-side AI failed: %s", error)
        return None, str(error)


@blueprint.get("/starters")
def starters():
    return jsonify(
        starters=list(STARTER_PROMPTS),
        actions=available_actions(),
        themes=detect_themes(""),
    )


@blueprint.post("/chat")
def chat():
    payload = ChatRequest.model_validate(_json_body())
    app = current_app._get_current_object()

    scripture, passage = _resolve_scripture(payload.reference)

    prompt = prepare_chat(
        message=payload.message,
        history=[ChatTurn(role=m.role, content=m.content) for m in payload.history],
        scripture=scripture,
        max_history=app.config.get("AI_MAX_HISTORY", 12),
    )

    reply, error = _try_server_completion(prompt)

    body = {
        "prompt": prompt.as_payload(),
        "context": prompt.context,
        "scripture": passage,
        "mode": "server" if reply else "browser",
        "reply": reply,
    }
    if error:
        body["warning"] = (
            "The configured AI provider could not be reached, so the request was "
            "handed back to your browser instead."
        )
    body["disclaimer"] = (
        "Great Church AI is a software tool for exploring Christian content. It is "
        "not God, a pastor, or a prophet, and it does not speak with divine authority."
    )
    return jsonify(body)


@blueprint.post("/study")
def study():
    payload = StudyRequest.model_validate(_json_body())

    scripture = None
    passage = None
    if payload.include_scripture:
        scripture, passage = _resolve_scripture(payload.reference)

    try:
        prompt = prepare_study(payload.reference, payload.action, scripture)
    except ValueError:
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_action",
                        "message": "That study action is not available.",
                        "status": 400,
                    }
                }
            ),
            400,
        )

    reply, error = _try_server_completion(prompt)

    body = {
        "prompt": prompt.as_payload(),
        "action": payload.action,
        "reference": passage.get("reference") if passage else payload.reference,
        "scripture": passage,
        "mode": "server" if reply else "browser",
        "reply": reply,
    }
    if error:
        body["warning"] = (
            "The configured AI provider could not be reached, so this study prompt "
            "will be handled in your browser."
        )
    return jsonify(body)


@blueprint.post("/prayer-draft")
def prayer_draft():
    """Prepare a prayer prompt from a freeform description of a situation."""
    payload = PrayerDraftRequest.model_validate(_json_body())

    scripture, passage = _resolve_scripture(payload.reference)
    prompt = prepare_prayer_draft(payload.situation, scripture=scripture)

    reply, error = _try_server_completion(prompt)

    body = {
        "prompt": prompt.as_payload(),
        "situation": payload.situation,
        "scripture": passage,
        "mode": "server" if reply else "browser",
        "reply": reply,
        "disclaimer": HUMANITY_NOTE,
    }
    if error:
        body["warning"] = (
            "The configured AI provider could not be reached, so this prayer prompt "
            "will be handled in your browser."
        )
    return jsonify(body)


@blueprint.post("/prayer-prompt")
def prayer_prompt():
    payload = PrayerRequest.model_validate(_json_body())
    prompt = prepare_prayer(payload.topic, payload.detail)

    reply, error = _try_server_completion(prompt)

    body = {
        "prompt": prompt.as_payload(),
        "topic": payload.topic,
        "mode": "server" if reply else "browser",
        "reply": reply,
    }
    if error:
        body["warning"] = (
            "The configured AI provider could not be reached, so this prayer prompt "
            "will be handled in your browser."
        )
    return jsonify(body)
