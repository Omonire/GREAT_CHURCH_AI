"""Themed verse catalogue.

King James Version text (1611, public domain) lives in the ``pythonbible_kjv``
data package and is read at runtime through
:mod:`church_ai_api.bible.corpus`. This module only holds the *references* and
the theme attached to each one, so the catalogue cannot drift out of sync with
the real text.

Used for the daily verse and for the clearly-labelled offline prayer fallback.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerseEntry:
    reference: str
    theme: str


#: (reference, theme) in display order.
_ENTRIES: tuple[tuple[str, str], ...] = (
    ("John 3:16", "love"),
    ("Psalm 23:1", "trust"),
    ("Psalm 46:1", "peace"),
    ("Philippians 4:13", "strength"),
    ("Proverbs 3:5", "wisdom"),
    ("Isaiah 40:31", "strength"),
    ("Romans 8:28", "guidance"),
    ("Matthew 6:33", "guidance"),
    ("Joshua 1:9", "courage"),
    ("Psalm 119:105", "scripture"),
    ("2 Timothy 3:16", "scripture"),
    ("Ephesians 2:8", "grace"),
    ("1 John 4:8", "love"),
    ("1 John 4:19", "love"),
    ("Colossians 3:23", "work"),
    ("James 1:5", "wisdom"),
    ("Galatians 5:22", "growth"),
    ("Romans 12:2", "growth"),
    ("Lamentations 3:22", "hope"),
    ("Psalm 34:8", "gratitude"),
    ("1 Thessalonians 5:16", "gratitude"),
    ("Psalm 37:4", "trust"),
    ("Hebrews 11:1", "faith"),
    ("2 Corinthians 5:7", "faith"),
    ("Mark 10:27", "faith"),
    ("Matthew 7:7", "prayer"),
    ("John 14:27", "peace"),
    ("Philippians 4:6-7", "peace"),
    ("1 Peter 5:7", "family"),
    ("Joshua 1:8", "studies"),
    ("Proverbs 4:23", "wisdom"),
    ("Ecclesiastes 12:13", "wisdom"),
    ("Psalm 127:1", "family"),
    ("Romans 12:12", "work"),
    ("Psalm 37:5", "guidance"),
    ("Romans 15:13", "hope"),
    ("Matthew 11:28", "rest"),
    ("Psalm 34:18", "comfort"),
    ("1 Peter 4:8", "relationships"),
    ("Matthew 5:14", "purpose"),
    ("Galatians 6:9", "perseverance"),
)

CATALOGUE: tuple[VerseEntry, ...] = tuple(
    VerseEntry(reference=reference, theme=theme) for reference, theme in _ENTRIES
)

THEMES: tuple[str, ...] = tuple(sorted({entry.theme for entry in CATALOGUE}))

_INDEX: dict[str, VerseEntry] = {
    " ".join(entry.reference.split()).lower(): entry for entry in CATALOGUE
}


def _normalise(reference: str) -> str:
    return " ".join((reference or "").strip().split()).lower()


def verse_by_reference(reference: str) -> VerseEntry | None:
    key = _normalise(reference)
    if not key:
        return None
    if key in _INDEX:
        return _INDEX[key]
    return _INDEX.get(key.replace(":", " "))


def entries_by_theme(theme: str) -> list[VerseEntry]:
    wanted = (theme or "").strip().lower()
    return [entry for entry in CATALOGUE if entry.theme == wanted]
