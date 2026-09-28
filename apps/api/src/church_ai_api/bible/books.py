"""Canonical book metadata for the 66 books of the Protestant canon."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class Book:
    name: str
    abbreviation: str
    chapters: int
    testament: str
    # Common alternative spellings users type.
    aliases: tuple[str, ...] = ()
    # Canonical 1-based position. Populated below; never set by hand.
    number: int = 0


OT: str = "Old Testament"
NT: str = "New Testament"

_RAW_BOOKS: tuple[Book, ...] = (
    Book("Genesis", "Gen", 50, OT, ("gen",)),
    Book("Exodus", "Exod", 40, OT, ("ex", "exo")),
    Book("Leviticus", "Lev", 27, OT, ("lev",)),
    Book("Numbers", "Num", 36, OT, ("num", "numbers")),
    Book("Deuteronomy", "Deut", 34, OT, ("deut", "deu", "deuteronomy")),
    Book("Joshua", "Josh", 24, OT, ("josh", "jos")),
    Book("Judges", "Judg", 21, OT, ("judg", "judges")),
    Book("Ruth", "Ruth", 4, OT, ("ruth",)),
    Book("1 Samuel", "1 Sam", 31, OT, ("1sam", "1samuel", "first samuel")),
    Book("2 Samuel", "2 Sam", 24, OT, ("2sam", "2samuel", "second samuel")),
    Book("1 Kings", "1 Kgs", 22, OT, ("1kgs", "1kings", "first kings")),
    Book("2 Kings", "2 Kgs", 25, OT, ("2kgs", "2kings", "second kings")),
    Book("1 Chronicles", "1 Chr", 29, OT, ("1chr", "1chronicles")),
    Book("2 Chronicles", "2 Chr", 36, OT, ("2chr", "2chronicles")),
    Book("Ezra", "Ezra", 10, OT, ("ezra",)),
    Book("Nehemiah", "Neh", 13, OT, ("neh", "nehemiah")),
    Book("Esther", "Esth", 10, OT, ("esther", "esth")),
    Book("Job", "Job", 42, OT, ("job",)),
    Book("Psalms", "Ps", 150, OT, ("psalm", "psalms", "psa")),
    Book("Proverbs", "Prov", 31, OT, ("proverb", "proverbs", "prv")),
    Book("Ecclesiastes", "Eccl", 12, OT, ("eccl", "ecclesiastes")),
    Book("Song of Solomon", "Song", 8, OT, ("song", "songs", "songofsolomon")),
    Book("Isaiah", "Isa", 66, OT, ("isa", "isaiah")),
    Book("Jeremiah", "Jer", 52, OT, ("jer", "jeremiah")),
    Book("Lamentations", "Lam", 5, OT, ("lam", "lamentations")),
    Book("Ezekiel", "Ezek", 48, OT, ("ezek", "ezekiel")),
    Book("Daniel", "Dan", 12, OT, ("dan", "daniel")),
    Book("Hosea", "Hos", 14, OT, ("hos", "hosea")),
    Book("Joel", "Joel", 3, OT, ("joel",)),
    Book("Amos", "Amos", 9, OT, ("amos",)),
    Book("Obadiah", "Obad", 1, OT, ("obad", "obadiah")),
    Book("Jonah", "Jonah", 4, OT, ("jon", "jonah")),
    Book("Micah", "Mic", 7, OT, ("mic", "micah")),
    Book("Nahum", "Nah", 3, OT, ("nah", "nahum")),
    Book("Habakkuk", "Hab", 3, OT, ("hab", "habakkuk")),
    Book("Zephaniah", "Zeph", 3, OT, ("zeph", "zephaniah")),
    Book("Haggai", "Hag", 2, OT, ("hag", "haggai")),
    Book("Zechariah", "Zech", 14, OT, ("zech", "zechariah")),
    Book("Malachi", "Mal", 4, OT, ("mal", "malachi")),
    Book("Matthew", "Matt", 28, NT, ("mat", "matthew", "matt")),
    Book("Mark", "Mark", 16, NT, ("mk", "mark")),
    Book("Luke", "Luke", 24, NT, ("luke", "lk")),
    Book("John", "John", 21, NT, ("jn", "jhn", "joh", "john")),
    Book("Acts", "Acts", 28, NT, ("act", "acts")),
    Book("Romans", "Rom", 16, NT, ("ro", "rom", "romans")),
    Book("1 Corinthians", "1 Cor", 16, NT, ("1cor", "1corinthians", "first corinthians")),
    Book("2 Corinthians", "2 Cor", 13, NT, ("2cor", "2corinthians", "second corinthians")),
    Book("Galatians", "Gal", 6, NT, ("gal", "galatians")),
    Book("Ephesians", "Eph", 6, NT, ("eph", "ephesians")),
    Book("Philippians", "Phil", 4, NT, ("phil", "philippians")),
    Book("Colossians", "Col", 4, NT, ("col", "colossians")),
    Book("1 Thessalonians", "1 Thess", 5, NT, ("1thess", "1thessalonians")),
    Book("2 Thessalonians", "2 Thess", 3, NT, ("2thess", "2thessalonians")),
    Book("1 Timothy", "1 Tim", 6, NT, ("1tim", "1timothy")),
    Book("2 Timothy", "2 Tim", 4, NT, ("2tim", "2timothy")),
    Book("Titus", "Titus", 3, NT, ("tit", "titus")),
    Book("Philemon", "Phlm", 1, NT, ("philemon", "phlm")),
    Book("Hebrews", "Heb", 13, NT, ("heb", "hebrews")),
    Book("James", "James", 5, NT, ("jas", "james", "jam")),
    Book("1 Peter", "1 Pet", 5, NT, ("1pet", "1peter", "first peter")),
    Book("2 Peter", "2 Pet", 3, NT, ("2pet", "2peter", "second peter")),
    Book("1 John", "1 John", 5, NT, ("1john", "first john")),
    Book("2 John", "2 John", 1, NT, ("2john", "second john")),
    Book("3 John", "3 John", 1, NT, ("3john", "third john")),
    Book("Jude", "Jude", 1, NT, ("jude",)),
    Book("Revelation", "Rev", 22, NT, ("revelation", "revelations")),
)

# Assign canonical positions once, rather than hand-numbering 66 literals.
BOOKS: tuple[Book, ...] = tuple(
    replace(book, number=position) for position, book in enumerate(_RAW_BOOKS, start=1)
)

BOOK_BY_NUMBER: dict[int, Book] = {book.number: book for book in BOOKS}


def _normalise(value: str) -> str:
    return value.strip().lower().replace(".", "")


def _build_index() -> dict[str, Book]:
    index: dict[str, Book] = {}
    for book in BOOKS:
        index[_normalise(book.name)] = book
        index[_normalise(book.abbreviation)] = book
        for alias in book.aliases:
            index[_normalise(alias)] = book
    return index


BOOK_INDEX: dict[str, Book] = _build_index()


# The formal name of a book of the Bible is plural, but a reference to it is
# written in the singular: "Psalm 23", not "Psalms 23". The pickers and stored
# data use the formal name; display code uses this.
_REFERENCE_NAMES: dict[str, str] = {
    "Psalms": "Psalm",
}


def reference_name(book: Book) -> str:
    """The book name as it should appear inside a reference."""
    return _REFERENCE_NAMES.get(book.name, book.name)


def find_book(name: str) -> Book | None:
    """Resolve a book by name, abbreviation, or alias. Case-insensitive."""
    if not name:
        return None
    return BOOK_INDEX.get(_normalise(name))


def books_in(testament: str | None = None) -> list[Book]:
    if testament is None:
        return list(BOOKS)
    wanted = testament.strip().lower()
    return [book for book in BOOKS if book.testament.lower() == wanted]


def book_names() -> list[str]:
    return [book.name for book in BOOKS]
