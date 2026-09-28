"""Local, public-domain Scripture corpus.

Reads the King James Version (1611) from the ``pythonbible_kjv`` data package.
KJV is in the public domain, so shipping it is legally fine, and it means the
core Scripture experience needs no network, no API key, and no rate limit.

The corpus is loaded lazily and cached per process. Loading takes roughly 0.1s
and building the text index roughly 0.25s, so the first search pays a small
one-off cost and everything after that is served from memory.
"""

from __future__ import annotations

import logging
import re
import threading

from church_ai_api.bible.books import BOOK_BY_NUMBER, BOOKS, Book, reference_name

logger = logging.getLogger(__name__)

# Titles pythonbible uses that differ from the names in books.py.
_TITLE_OVERRIDES: dict[str, str] = {
    "songofsongs": "Song of Solomon",
    "psalms": "Psalms",
}

_VERSE_PREFIX = re.compile(r"^\s*\d{1,3}\s*[.)]?\s*")
_BOOK_MULTIPLIER = 1_000_000


class CorpusUnavailable(Exception):
    """The bundled Scripture data is not installed."""


class CorpusEmpty(Exception):
    """The requested passage has no text."""


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower())


def _verse_id(book: Book, chapter: int, verse: int) -> int:
    return book.number * _BOOK_MULTIPLIER + chapter * 1000 + verse


def _index_chapters(texts: dict[int, str]) -> dict[tuple[int, int], list[int]]:
    """Group verse ids by (book, chapter), each list in verse order.

    Built from the ids that actually exist rather than by counting up to the
    book's chapter total. A chapter can have more verses than the book has
    chapters — John 3 has 36 verses and 21 chapters — so guessing the upper
    bound would silently drop verses.
    """
    grouped: dict[tuple[int, int], list[int]] = {}
    for verse_id in texts:
        book_number, remainder = divmod(verse_id, _BOOK_MULTIPLIER)
        chapter, verse = divmod(remainder, 1000)
        grouped.setdefault((book_number, chapter), []).append(verse)
    for verses in grouped.values():
        verses.sort()
    return grouped


class ScriptureCorpus:
    """Read-only view over the bundled KJV text."""

    def __init__(self) -> None:
        self._bible = None
        self._texts: dict[int, str] = {}
        self._lower: dict[int, str] = {}
        self._chapters: dict[tuple[int, int], list[int]] = {}
        self._lock = threading.Lock()
        self._loaded = False

    # -- loading ---------------------------------------------------------
    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                from pythonbible import get_bible
                from pythonbible.versions import Version
            except ImportError as error:  # pragma: no cover - packaging issue
                raise CorpusUnavailable(
                    "The bundled Scripture data (pythonbible_kjv) is not installed."
                ) from error

            try:
                bible = get_bible(Version.KING_JAMES, "plain_text")
            except Exception as error:  # MissingBiblePackageError and friends
                raise CorpusUnavailable(
                    "The bundled Scripture data (pythonbible_kjv) is not installed."
                ) from error

            indices = bible.verse_start_indices
            content = bible.scripture_content
            ordered = sorted(indices)
            total = len(ordered)

            texts: dict[int, str] = {}
            for position, verse_id in enumerate(ordered):
                start = indices[verse_id]
                end = indices[ordered[position + 1]] if position + 1 < total else len(content)
                texts[verse_id] = _VERSE_PREFIX.sub("", content[start:end]).strip()

            self._bible = bible
            self._texts = texts
            self._lower = {key: value.lower() for key, value in texts.items()}
            self._chapters = _index_chapters(texts)
            self._loaded = True
            logger.info("Loaded %d verses of bundled KJV text", len(texts))

    @property
    def available(self) -> bool:
        try:
            self._load()
        except CorpusUnavailable:
            return False
        return True

    def verse_count(self) -> int:
        self._load()
        return len(self._texts)

    # -- reading ---------------------------------------------------------
    def text_for(self, book: Book, chapter: int, verse: int) -> str:
        self._load()
        text = self._texts.get(_verse_id(book, chapter, verse))
        if not text:
            raise CorpusEmpty(f"No text for {book.name} {chapter}:{verse}.")
        return text

    def chapter_verses(self, book: Book, chapter: int) -> list[tuple[int, str]]:
        self._load()
        out: list[tuple[int, str]] = []
        for verse in self._chapters.get((book.number, chapter), ()):
            text = self._texts.get(_verse_id(book, chapter, verse))
            if text:
                out.append((verse, text))
        return out

    # -- search ----------------------------------------------------------
    def search(self, term: str, limit: int = 20) -> list[dict]:
        """Full-text search across the whole Bible.

        Multi-word queries require every word to appear in the verse, which
        keeps results relevant. Matching is substring-based so partial words
        work while the user is still typing.
        """
        self._load()
        needle = term.strip().lower()
        if not needle:
            return []

        words = [w for w in re.split(r"\s+", needle) if w]
        if not words:
            return []

        hits: list[dict] = []
        for verse_id, haystack in self._lower.items():
            if not all(word in haystack for word in words):
                continue
            book = BOOK_BY_NUMBER.get(verse_id // _BOOK_MULTIPLIER)
            if book is None:
                continue
            chapter = (verse_id % _BOOK_MULTIPLIER) // 1000
            verse = verse_id % 1000
            hits.append(
                {
                    "reference": f"{reference_name(book)} {chapter}:{verse}",
                    "book": book.name,
                    "testament": book.testament,
                    "chapter": chapter,
                    "verse": verse,
                    "text": self._texts[verse_id],
                }
            )
            if len(hits) >= limit:
                break

        return hits


_corpus: ScriptureCorpus | None = None


def get_corpus() -> ScriptureCorpus:
    """Return the process-wide corpus, creating it on first use."""
    global _corpus
    if _corpus is None:
        _corpus = ScriptureCorpus()
    return _corpus
