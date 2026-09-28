"""Scripture domain: canon metadata, reference parsing, and text lookup."""

from church_ai_api.bible.books import BOOK_BY_NUMBER, Book, find_book
from church_ai_api.bible.corpus import CorpusEmpty, CorpusUnavailable, get_corpus
from church_ai_api.bible.reference import ScriptureReference, parse_reference
from church_ai_api.bible.service import ScriptureError, ScriptureService

__all__ = [
    "BOOK_BY_NUMBER",
    "Book",
    "CorpusEmpty",
    "CorpusUnavailable",
    "ScriptureError",
    "ScriptureReference",
    "ScriptureService",
    "find_book",
    "get_corpus",
    "parse_reference",
]
