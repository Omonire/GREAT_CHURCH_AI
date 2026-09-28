"""Sermon notes and the outline endpoint.

Two guarantees: every stored note is marked as demonstration material, and the
outline endpoint refuses to guess at a passage it cannot read.
"""

import pytest

from church_ai_api.services.sermon import (
    DEMO_NOTES,
    OUTLINE_DISCLAIMER,
    blank_note_template,
    get_note,
    list_notes,
)


# --- demonstration notes -----------------------------------------------


def test_every_note_is_marked_as_demonstration() -> None:
    notes = list_notes()
    assert notes
    for note in notes:
        assert note["demo"] is True


def test_notes_carry_a_reference_and_real_content() -> None:
    for note in list_notes():
        assert note["passage"]
        assert note["summary"]
        assert note["key_points"]
        assert note["reflection_questions"]


def test_note_ids_are_unique() -> None:
    ids = [note.id for note in DEMO_NOTES]
    assert len(ids) == len(set(ids))


def test_get_note_is_case_insensitive() -> None:
    assert get_note("DEMO-WAITING") is not None
    assert get_note("  demo-waiting  ") is not None


def test_get_note_returns_none_for_unknown_ids() -> None:
    assert get_note("nope") is None
    assert get_note("") is None


def test_blank_template_is_not_demo_content() -> None:
    template = blank_note_template()
    assert template["demo"] is False
    assert template["editable"] is True
    assert template["summary"] == ""


# --- endpoints ---------------------------------------------------------


def test_notes_endpoint_disclaims_its_content(client) -> None:
    body = client.get("/api/sermons").get_json()
    assert len(body["notes"]) == len(DEMO_NOTES)
    assert "Demonstration content" in body["disclaimer"]


def test_note_detail_endpoint(client) -> None:
    body = client.get("/api/sermons/demo-waiting").get_json()
    assert body["note"]["id"] == "demo-waiting"
    assert body["note"]["demo"] is True
    assert body["disclaimer"]


def test_note_detail_404s_for_an_unknown_id(client) -> None:
    response = client.get("/api/sermons/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_template_endpoint(client) -> None:
    body = client.get("/api/sermons/template").get_json()
    assert body["template"]["demo"] is False


# --- outline -----------------------------------------------------------


def test_outline_endpoint_grounds_the_prompt_in_real_text(client) -> None:
    response = client.post(
        "/api/sermons/outline",
        json={"reference": "Psalm 23", "title": "The Good Shepherd", "body": "Focus on verse 4"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["mode"] == "browser"
    assert body["reference"] == "Psalm 23"
    assert body["verse_count"] == 6
    assert body["translation"] == "King James Version"
    assert "scaffolding outline" in body["prompt"]["system"]

    instruction = body["prompt"]["messages"][-1]["content"]
    assert "The Good Shepherd" in instruction
    assert "Focus on verse 4" in instruction


def test_outline_endpoint_includes_the_verse_text(client) -> None:
    body = client.post("/api/sermons/outline", json={"reference": "John 3:16"}).get_json()
    assert "God so loved the world" in body["prompt"]["system"]


def test_outline_endpoint_normalises_the_reference(client) -> None:
    body = client.post("/api/sermons/outline", json={"reference": "ps 23"}).get_json()
    assert body["reference"] == "Psalm 23"


def test_outline_endpoint_refuses_to_guess_a_bad_reference(client) -> None:
    response = client.post(
        "/api/sermons/outline", json={"reference": "Hobbits 1:1"}
    )
    body = response.get_json()

    assert response.status_code == 400
    assert "could not be read" in body["error"]["message"]
    assert "prompt" not in body


def test_outline_endpoint_rejects_an_out_of_range_chapter(client) -> None:
    response = client.post("/api/sermons/outline", json={"reference": "John 99"})
    assert response.status_code == 400


def test_outline_endpoint_requires_a_reference(client) -> None:
    response = client.post("/api/sermons/outline", json={})
    assert response.status_code == 400


def test_outline_endpoint_rejects_an_oversized_reference(client) -> None:
    response = client.post("/api/sermons/outline", json={"reference": "J" * 200})
    assert response.status_code == 400


def test_outline_disclaimer_says_it_is_not_a_sermon() -> None:
    lowered = OUTLINE_DISCLAIMER.lower()
    assert "not a sermon" in lowered
    assert "not the word of god" in lowered


# --- summarise ---------------------------------------------------------


def test_summarise_endpoint_needs_text(client) -> None:
    response = client.post("/api/sermons/summarise", json={"title": "My note"})
    assert response.status_code == 400
    assert "no note text" in response.get_json()["error"]["message"]


def test_summarise_endpoint_rejects_an_oversized_note(client) -> None:
    response = client.post(
        "/api/sermons/summarise", json={"title": "x", "body": "y" * 9000}
    )
    assert response.status_code == 400


def test_summarise_endpoint_returns_a_prompt(client) -> None:
    body = client.post(
        "/api/sermons/summarise",
        json={"title": "Sermon on Psalm 23", "body": "The shepherd leads."},
    ).get_json()
    assert body["mode"] == "browser"
    assert body["prompt"]["messages"]
    assert body["disclaimer"]
