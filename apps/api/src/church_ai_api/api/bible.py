"""Scripture endpoints: books, passages, search, and the daily verse."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from church_ai_api.bible.books import find_book
from church_ai_api.bible.service import ScriptureError, get_scripture_service

logger = logging.getLogger(__name__)

blueprint = Blueprint("bible", __name__, url_prefix="/api/bible")

MAX_REFERENCE_LENGTH = 80


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message, "status": status}}), status


@blueprint.get("/books")
def books():
    return jsonify(get_scripture_service().list_books())


@blueprint.get("/reference")
def reference():
    raw = (request.args.get("reference") or "").strip()
    if not raw:
        return _error(
            "invalid_reference",
            "Tell us which passage to read, for example John 3:16.",
            400,
        )
    if len(raw) > MAX_REFERENCE_LENGTH:
        return _error("invalid_reference", "That reference is too long to look up.", 400)

    try:
        return jsonify(get_scripture_service().get_reference(raw))
    except ScriptureError as error:
        return _error(error.code, str(error), error.status)


@blueprint.get("/book")
def book():
    name = (request.args.get("book") or "").strip()
    chapter_raw = (request.args.get("chapter") or "").strip()

    if not name or not chapter_raw:
        return _error(
            "invalid_request",
            "A book and a chapter are both needed to read a passage.",
            400,
        )

    resolved = find_book(name)
    if resolved is None:
        return _error("unknown_book", "We do not recognise that book of the Bible.", 404)

    try:
        chapter = int(chapter_raw)
    except ValueError:
        return _error("invalid_chapter", "Chapter numbers are written as plain digits.", 400)

    if not 1 <= chapter <= resolved.chapters:
        return _error(
            "invalid_chapter",
            f"{resolved.name} has {resolved.chapters} chapters, so {chapter} is out of range.",
            400,
        )

    try:
        return jsonify(
            get_scripture_service().get_reference(f"{resolved.name} {chapter}")
        )
    except ScriptureError as error:
        return _error(error.code, str(error), error.status)


@blueprint.get("/chapter")
def chapter():
    """Alias of /book kept for clarity in client code."""
    return book()


@blueprint.get("/search")
def search():
    query = (request.args.get("q") or request.args.get("query") or "").strip()
    if len(query) < 2:
        return _error("invalid_query", "Enter at least two characters to search.", 400)
    if len(query) > 120:
        return _error("invalid_query", "That search is too long.", 400)

    try:
        limit = int(request.args.get("limit") or 20)
    except ValueError:
        limit = 20

    try:
        return jsonify(get_scripture_service().search(query, limit=limit))
    except ScriptureError as error:
        return _error(error.code, str(error), error.status)


@blueprint.get("/verse-of-the-day")
def verse_of_the_day():
    return jsonify(get_scripture_service().verse_of_the_day())


@blueprint.get("/themes")
def themes():
    return jsonify(get_scripture_service().themes())
