"""Sermon and note endpoints.

Two very different things live here and they are kept apart on purpose:

* ``/api/sermons`` and ``/api/sermons/<id>`` return *demonstration* notes. Every
  one of them carries ``demo: True`` and the response repeats the disclaimer, so
  they can never be mistaken for a recording of a real church service.
* ``/api/sermons/outline`` builds a *prompt* for a passage the user names. It
  never invents Scripture: the passage text is pulled from the bundled KJV and
  passed to the model, and if the text cannot be found the response says so
  instead of guessing.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from church_ai_api.ai.prompts import prepare_sermon_outline, prepare_study
from church_ai_api.ai.provider import ProviderError, ServerProvider
from church_ai_api.bible.service import ScriptureError, get_scripture_service
from church_ai_api.schemas.requests import OutlineRequest, StudyRequest
from church_ai_api.services.sermon import (
    DEMO_NOTE_DISCLAIMER,
    OUTLINE_DISCLAIMER,
    blank_note_template,
    get_note,
    list_notes,
)

logger = logging.getLogger(__name__)

blueprint = Blueprint("sermons", __name__)


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message, "status": status}}), status


def _try_server_completion(prompt) -> tuple[str | None, str | None]:
    provider = ServerProvider()
    if not provider.enabled:
        return None, None
    try:
        return provider.complete(prompt), None
    except ProviderError as error:
        logger.warning("Server-side AI failed: %s", error)
        return None, str(error)


@blueprint.get("/api/sermons")
def index():
    return jsonify(notes=list_notes(), disclaimer=DEMO_NOTE_DISCLAIMER)


@blueprint.get("/api/sermons/template")
def template():
    return jsonify(template=blank_note_template(), disclaimer=DEMO_NOTE_DISCLAIMER)


@blueprint.get("/api/sermons/<note_id>")
def detail(note_id: str):
    note = get_note(note_id)
    if note is None:
        return _error("not_found", "We could not find that note.", 404)
    return jsonify(note=note.as_dict(), disclaimer=DEMO_NOTE_DISCLAIMER)


@blueprint.post("/api/sermons/outline")
def outline():
    """Prepare a preaching-outline prompt grounded in the bundled KJV text."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("invalid_request", "Send the passage you want an outline for.", 400)

    try:
        payload = OutlineRequest.model_validate(data)
    except Exception:
        return _error("invalid_request", "That request could not be read.", 400)

    reference = payload.reference
    passage = None

    try:
        passage = get_scripture_service().get_reference(reference)
        reference = passage["reference"]
    except ScriptureError as error:
        # Never fabricate a passage. If the text cannot be found the response
        # says so rather than letting the model guess at it.
        logger.info("Sermon outline skipped text for %r: %s", reference, error)
        return _error(
            error.code,
            f"The text for {reference} could not be read: {error}",
            error.status,
        )

    verses = passage.get("verses") or []
    scripture = "\n".join(
        f"{verse['verse']}. {verse['text']}" for verse in verses
    )

    prompt = prepare_sermon_outline(
        reference=reference,
        scripture=scripture,
        title=payload.title,
        notes=payload.body,
    )

    reply, error = _try_server_completion(prompt)

    body = {
        "prompt": prompt.as_payload(),
        "reference": reference,
        "translation": passage.get("translation"),
        "verse_count": len(verses),
        "mode": "server" if reply else "browser",
        "reply": reply,
        "disclaimer": OUTLINE_DISCLAIMER,
    }
    if error:
        body["warning"] = (
            "The configured AI provider could not be reached, so this outline will be "
            "generated in your browser instead."
        )
    return jsonify(body)


@blueprint.post("/api/sermons/summarise")
def summarise():
    """Prepare a summary prompt for a note the user is writing themselves."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("invalid_request", "Send the note text you want summarised.", 400)

    try:
        payload = StudyRequest.model_validate(
            {
                "reference": data.get("title") or "this note",
                "action": "summarize",
            }
        )
    except Exception:
        return _error("invalid_request", "That note could not be read.", 400)

    body = (data.get("body") or "").strip()
    if not body:
        return _error("invalid_request", "There is no note text to summarise yet.", 400)
    if len(body) > 8000:
        return _error("invalid_request", "That note is too long to summarise in one go.", 400)

    prompt = prepare_study(payload.reference, "summarize", scripture=None)
    return jsonify(
        prompt=prompt.as_payload(),
        mode="browser",
        disclaimer=DEMO_NOTE_DISCLAIMER,
    )
