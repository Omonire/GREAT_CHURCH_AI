"""Scripture lookup over the bundled public-domain KJV corpus.

There is one source of truth: the local corpus. If the KJV data package is not
installed the service raises ``ScriptureError`` and the API returns a clear 503
rather than inventing text or quietly returning nothing.
"""

from __future__ import annotations

import datetime as _dt
import logging

from church_ai_api.bible.books import books_in, reference_name
from church_ai_api.bible.corpus import (
    BOOK_BY_NUMBER,
    CorpusEmpty,
    CorpusUnavailable,
    get_corpus,
)
from church_ai_api.bible.reference import ScriptureReference, parse_reference
from church_ai_api.bible.verses import THEMES, verse_by_reference
from church_ai_api.config import Settings, get_settings

logger = logging.getLogger(__name__)

TRANSLATION_NAME = "King James Version"
TRANSLATION_SHORT = "KJV"


class ScriptureError(Exception):
    """Raised when a passage cannot be served.

    ``status`` tells the API layer how to answer. A reference we could not parse
    is the caller's mistake (400); a passage missing from an otherwise working
    corpus is a 404; a corpus that will not load at all is a 503.
    """

    def __init__(self, message: str, status: int = 503, code: str = "scripture_unavailable") -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class ScriptureService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def _corpus(self):
        try:
            return get_corpus()
        except CorpusUnavailable as error:
            raise ScriptureError(str(error)) from error

    # -- metadata --------------------------------------------------------
    def list_books(self) -> dict:
        def entry(book) -> dict:
            return {"name": book.name, "chapters": book.chapters}

        return {
            "source": "bundled",
            "degraded": False,
            "translation": TRANSLATION_NAME,
            "translation_short": TRANSLATION_SHORT,
            "count": len(books_in()),
            "testaments": {
                "old": [entry(book) for book in books_in("Old Testament")],
                "new": [entry(book) for book in books_in("New Testament")],
            },
        }

    def themes(self) -> dict:
        return {"themes": list(THEMES)}

    # -- reading ---------------------------------------------------------
    def get_reference(self, raw: str) -> dict:
        reference = parse_reference(raw)
        if reference is None:
            raise ScriptureError(
                "We could not read that reference. Try a format like John 3:16.",
                status=400,
                code="invalid_reference",
            )
        return self.get_parsed_reference(reference)

    def get_parsed_reference(self, reference: ScriptureReference) -> dict:
        corpus = self._corpus
        book = reference.book

        skipped: list[int] = []

        if reference.whole_chapter:
            try:
                pairs = corpus.chapter_verses(book, reference.chapter)
            except CorpusUnavailable as error:
                raise ScriptureError(str(error)) from error
            if not pairs:
                raise ScriptureError(
                    f"{reference_name(book)} {reference.chapter} is not available "
                    "in the bundled text.",
                    status=404,
                    code="passage_not_found",
                )
            verses = [{"verse": number, "text": text} for number, text in pairs]
        else:
            verses = []
            for number in reference.all_verses:
                try:
                    verses.append({"verse": number, "text": corpus.text_for(book, reference.chapter, number)})
                except CorpusEmpty:
                    skipped.append(number)
            if not verses:
                raise ScriptureError(
                    f"{reference_name(book)} {reference.chapter} is not available "
                    "in the bundled text.",
                    status=404,
                    code="passage_not_found",
                )

        payload = {
            "reference": reference.display,
            "book": book.name,
            "testament": book.testament,
            "chapter": reference.chapter,
            "translation": TRANSLATION_NAME,
            "translation_short": TRANSLATION_SHORT,
            "text": " ".join(item["text"] for item in verses),
            "verses": verses,
            "source": "bundled",
            "degraded": False,
        }
        if skipped:
            payload["warning"] = (
                "These verse numbers are not in the bundled text and were left out: "
                + ", ".join(str(number) for number in skipped)
                + "."
            )
        return payload

    # -- search ----------------------------------------------------------
    def search(self, query: str, limit: int = 20) -> dict:
        term = (query or "").strip()
        if len(term) < 2:
            raise ScriptureError(
                "Enter at least two characters to search.",
                status=400,
                code="invalid_query",
            )

        limit = max(1, min(int(limit or 20), 50))
        corpus = self._corpus

        try:
            results = corpus.search(term, limit=limit)
        except CorpusUnavailable as error:
            raise ScriptureError(str(error)) from error

        return {
            "query": term,
            "count": len(results),
            "results": results,
            "translation": TRANSLATION_NAME,
            "translation_short": TRANSLATION_SHORT,
            "source": "bundled",
            "degraded": False,
        }

    # -- daily verse -----------------------------------------------------
    def verse_of_the_day(self) -> dict:
        """Deterministic daily verse from the themed catalogue.

        Selection is by calendar day so the verse is stable within the day, and
        the response says plainly that the choice is algorithmic, not divine.
        """
        from church_ai_api.bible.verses import CATALOGUE

        today = _dt.date.today()
        entry = CATALOGUE[today.toordinal() % len(CATALOGUE)]
        corpus = self._corpus

        reference = parse_reference(entry.reference)
        text = ""
        if reference is not None:
            try:
                text = corpus.text_for(
                    reference.book, reference.chapter, reference.all_verses[0]
                )
            except (CorpusEmpty, CorpusUnavailable):
                pass

        return {
            "reference": entry.reference,
            "text": text,
            "theme": entry.theme,
            "date": today.isoformat(),
            "translation": TRANSLATION_NAME,
            "translation_short": TRANSLATION_SHORT,
            "source": "bundled",
            "degraded": False,
            "selection": "algorithmic",
            "note": (
                "This verse is selected automatically for today's date. It is not "
                "a divine selection."
            ),
        }


_service: ScriptureService | None = None


def get_scripture_service() -> ScriptureService:
    global _service
    if _service is None:
        _service = ScriptureService()
    return _service


__all__ = [
    "BOOK_BY_NUMBER",
    "ScriptureError",
    "ScriptureService",
    "get_scripture_service",
    "verse_by_reference",
]
