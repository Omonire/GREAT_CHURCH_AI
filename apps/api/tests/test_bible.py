"""Scripture reading, search, and the daily verse.

These run against the bundled KJV, so they also prove the data package is
installed and the corpus actually loads.
"""

import pytest

from church_ai_api.bible.books import find_book, reference_name
from church_ai_api.bible.corpus import get_corpus
from church_ai_api.bible.reference import parse_reference


# --- reference parsing -------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("John 3:16", "John 3:16"),
        ("john 3.16", "John 3:16"),
        ("JHN 3.16", "John 3:16"),
        ("1 Corinthians 13:4-7", "1 Corinthians 13:4-7"),
        ("1 Cor 13:4–7", "1 Corinthians 13:4-7"),
        ("Ps 23", "Psalm 23"),
        ("Psalm 23:1-3", "Psalm 23:1-3"),
        ("Rom 8:28, 30", "Romans 8:28, 30"),
        ("Heb 11", "Hebrews 11"),
        ("please read John 3:16", "John 3:16"),
        ("Song of Songs 2:1", "Song of Solomon 2:1"),
    ],
)
def test_reference_display(raw: str, expected: str) -> None:
    reference = parse_reference(raw)
    assert reference is not None, f"failed to parse {raw!r}"
    assert reference.display == expected


def test_reference_reversed_range_is_normalised() -> None:
    reference = parse_reference("John 3:16-14")
    assert reference is not None
    assert reference.display == "John 3:14-16"


@pytest.mark.parametrize("raw", ["", "   ", "zzz 9", "not a reference", "John"])
def test_unparseable_reference_returns_none(raw: str) -> None:
    assert parse_reference(raw) is None


def test_reference_name_uses_singular_for_psalms() -> None:
    book = find_book("psalms")
    assert book is not None
    assert book.name == "Psalms"
    assert reference_name(book) == "Psalm"


# --- corpus ------------------------------------------------------------


def test_corpus_loads_every_verse() -> None:
    corpus = get_corpus()
    assert corpus.verse_count() == 31_102


def test_corpus_returns_real_text() -> None:
    book = find_book("John")
    text = get_corpus().text_for(book, 3, 16)
    assert "God so loved the world" in text
    assert "John 3:16" not in text  # the verse number is stripped


# --- endpoints ---------------------------------------------------------


def test_books_lists_all_66_with_chapter_counts(client) -> None:
    body = client.get("/api/bible/books").get_json()

    assert body["count"] == 66
    assert body["source"] == "bundled"
    assert body["degraded"] is False
    assert body["translation"] == "King James Version"

    old = body["testaments"]["old"]
    new = body["testaments"]["new"]
    assert len(old) == 39
    assert len(new) == 27
    assert old[0] == {"name": "Genesis", "chapters": 50}
    assert new[-1] == {"name": "Revelation", "chapters": 22}


def test_reference_endpoint_returns_verses(client) -> None:
    response = client.get("/api/bible/reference", query_string={"reference": "John 3:16"})
    body = response.get_json()

    assert response.status_code == 200
    assert body["reference"] == "John 3:16"
    assert body["translation_short"] == "KJV"
    assert len(body["verses"]) == 1
    assert body["verses"][0]["verse"] == 16
    assert "God so loved the world" in body["verses"][0]["text"]


def test_reference_endpoint_reads_a_whole_chapter(client) -> None:
    body = client.get("/api/bible/reference", query_string={"reference": "Ps 23"}).get_json()
    assert body["reference"] == "Psalm 23"
    assert len(body["verses"]) == 6
    assert body["verses"][0]["verse"] == 1


def test_reference_endpoint_reads_a_range(client) -> None:
    body = client.get(
        "/api/bible/reference", query_string={"reference": "1 Cor 13:4-7"}
    ).get_json()
    assert [v["verse"] for v in body["verses"]] == [4, 5, 6, 7]


def test_malformed_reference_is_a_client_error(client) -> None:
    response = client.get("/api/bible/reference", query_string={"reference": "zzz 9"})
    body = response.get_json()

    assert response.status_code == 400
    assert body["error"]["code"] == "invalid_reference"


def test_missing_reference_query_is_a_client_error(client) -> None:
    response = client.get("/api/bible/reference")
    assert response.status_code == 400


def test_book_endpoint(client) -> None:
    body = client.get("/api/bible/book", query_string={"book": "John", "chapter": "3"}).get_json()
    assert body["reference"] == "John 3"
    assert len(body["verses"]) == 36


def test_book_endpoint_rejects_unknown_book(client) -> None:
    response = client.get("/api/bible/book", query_string={"book": "Hobbits", "chapter": "1"})
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "unknown_book"


def test_book_endpoint_rejects_out_of_range_chapter(client) -> None:
    response = client.get("/api/bible/book", query_string={"book": "John", "chapter": "99"})
    assert response.status_code == 400
    assert "chapters" in response.get_json()["error"]["message"]


def test_search_requires_two_characters(client) -> None:
    response = client.get("/api/bible/search", query_string={"q": "a"})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_query"


def test_search_finds_real_verses(client) -> None:
    body = client.get("/api/bible/search", query_string={"q": "shepherd", "limit": 5}).get_json()

    assert body["count"] > 0
    assert body["count"] <= 5
    first = body["results"][0]
    assert "shepherd" in first["text"].lower()
    assert ":" in first["reference"]
    assert first["book"] and first["chapter"] and first["verse"]


def test_search_requires_every_word(client) -> None:
    body = client.get("/api/bible/search", query_string={"q": "shepherd psalm"}).get_json()
    for result in body["results"]:
        lowered = result["text"].lower()
        assert "shepherd" in lowered
        assert "psalm" in lowered


def test_search_respects_the_limit(client) -> None:
    body = client.get("/api/bible/search", query_string={"q": "the", "limit": 3}).get_json()
    assert len(body["results"]) == 3


def test_daily_verse_is_real_text_and_says_it_is_algorithmic(client) -> None:
    body = client.get("/api/bible/verse-of-the-day").get_json()

    assert body["selection"] == "algorithmic"
    assert "not" in body["note"].lower() and "divine" in body["note"].lower()
    assert body["translation"] == "King James Version"
    assert body["theme"]
    assert body["text"], "the daily verse must resolve to real KJV text"

    reference = parse_reference(body["reference"])
    assert reference is not None
