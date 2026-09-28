"""Parse and normalise human-written Scripture references.

Supports forms such as::

    John 3:16
    john 3.16
    1 Corinthians 13:4-7
    Ps 23
    Psalm 23:1-3
    Romans 8:28, 30
    Hebrews 11
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from church_ai_api.bible.books import Book, find_book, reference_name

# Book names may contain digits (1/2/3 John), apostrophes, spaces, and periods.
_BOOK = r"(?:\d\s*)?[A-Za-z][A-Za-z'.\s]*"
# A chapter/verse separator may be a colon or a full stop: "John 3:16", "John 3.16".
_REFERENCE = re.compile(
    rf"^\s*(?P<book>{_BOOK}?)\s*"
    r"(?P<chapter>\d{1,3})\s*"
    r"(?:[:.]\s*(?P<verses>\d{1,3}(?:\s*[-–—]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–—]\s*\d{1,3})?)*))?\s*"
    r"(?P<trailing>[A-Za-z]{0,3})\s*$"
)

_RANGE = re.compile(r"^\s*(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*$")


@dataclass(frozen=True, slots=True)
class VerseRange:
    start: int
    end: int

    def __iter__(self):  # pragma: no cover - convenience
        yield self.start
        yield self.end

    def to_list(self) -> list[int]:
        return list(range(self.start, self.end + 1))


@dataclass(frozen=True, slots=True)
class ScriptureReference:
    book: Book
    chapter: int
    ranges: tuple[VerseRange, ...]
    trailing: str = ""

    @property
    def display(self) -> str:
        parts = []
        for item in self.ranges:
            parts.append(
                str(item.start) if item.start == item.end else f"{item.start}-{item.end}"
            )
        chapter = f"{reference_name(self.book)} {self.chapter}"
        if not parts:
            return chapter
        return f"{chapter}:{', '.join(parts)}"

    @property
    def all_verses(self) -> list[int]:
        verses: list[int] = []
        for item in self.ranges:
            verses.extend(item.to_list())
        return verses

    @property
    def whole_chapter(self) -> bool:
        return not self.ranges


def _parse_ranges(raw: str) -> tuple[VerseRange, ...]:
    ranges: list[VerseRange] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = _RANGE.match(chunk)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            if start > end:
                start, end = end, start
            ranges.append(VerseRange(start, end))
        else:
            number = int(chunk)
            ranges.append(VerseRange(number, number))
    return tuple(ranges)


def parse_reference(raw: str) -> ScriptureReference | None:
    """Parse a reference string. Returns ``None`` when it cannot be understood."""
    if not raw or not raw.strip():
        return None

    text = raw.strip()
    # Search the whole string so "please read John 3:16" also resolves.
    for candidate in _iter_candidates(text):
        match = _REFERENCE.match(candidate)
        if not match:
            continue

        book = find_book(match.group("book"))
        if book is None:
            continue

        chapter = int(match.group("chapter"))
        if not 1 <= chapter <= book.chapters:
            continue

        verses_raw = match.group("verses")
        ranges = _parse_ranges(verses_raw) if verses_raw else ()

        if ranges:
            highest = max(item.end for item in ranges)
            if highest < 1:
                continue

        return ScriptureReference(
            book=book,
            chapter=chapter,
            ranges=ranges,
            trailing=match.group("trailing") or "",
        )

    return None


def _iter_candidates(text: str) -> list[str]:
    """Yield progressively trimmed substrings to find an embedded reference."""
    cleaned = re.sub(r"[«»\"'“”‘’()\[\]]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    candidates = [cleaned]
    # Trim leading words one at a time ("please read John 3:16" -> "John 3:16").
    tokens = cleaned.split(" ")
    for index in range(1, len(tokens)):
        candidates.append(" ".join(tokens[index:]))
    return candidates
