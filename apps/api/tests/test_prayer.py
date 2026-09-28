"""Prayer assembly and the sermon-note endpoints.

The rule these tests protect: a fixed template is never presented as a generated
prayer, and a passage is never invented when one cannot be read.
"""

import pytest

from church_ai_api.services.prayer import (
    PRAYER_TOPICS,
    build_offline_prayer,
    get_topic,
    list_topics,
    resolve_anchor,
)


# --- topics ------------------------------------------------------------


def test_every_topic_has_a_label_and_hint() -> None:
    for topic in PRAYER_TOPICS:
        assert topic.label
        assert topic.prompt_hint
        assert topic.id == topic.id.strip().lower()


def test_list_topics_exposes_what_the_picker_needs() -> None:
    topics = list_topics()
    assert len(topics) == len(PRAYER_TOPICS)
    for topic in topics:
        assert topic["label"]
        assert topic["scripture"], "each topic should show an anchoring passage"
        assert topic["id"] == topic["slug"]


def test_get_topic_falls_back_for_unknown_ids() -> None:
    assert get_topic("not-a-real-topic").id == "reflection"
    assert get_topic("PEACE").id == "peace"


# --- anchors -----------------------------------------------------------


def test_resolve_anchor_returns_real_text() -> None:
    anchor = resolve_anchor("Psalm 34:18")
    assert anchor is not None
    assert anchor["reference"] == "Psalm 34:18"
    assert "broken heart" in anchor["text"]


def test_resolve_anchor_returns_none_for_nonsense() -> None:
    assert resolve_anchor("not a passage") is None
    assert resolve_anchor("") is None
    assert resolve_anchor(None) is None


# --- offline prayer ----------------------------------------------------


def test_offline_prayer_is_labelled_as_not_ai() -> None:
    prayer = build_offline_prayer("peace")
    assert prayer["source"] == "offline"
    assert prayer["degraded"] is True
    assert "not a generated prayer" in prayer["disclaimer"]


def test_offline_prayer_uses_the_named_passage() -> None:
    prayer = build_offline_prayer("sorrow", reference="Psalm 34:18")
    assert prayer["reference"] == "Psalm 34:18"
    assert prayer["anchor_scripture"]["text"]
    assert "Psalm 34:18 says" in prayer["text"]


def test_offline_prayer_warns_when_the_reference_is_unreadable() -> None:
    prayer = build_offline_prayer("peace", reference="Hobbits 1:1")
    assert "could not be read" in prayer["warning"]
    # It must still quote a real verse rather than nothing at all.
    assert prayer["anchor_scripture"]["reference"]


def test_offline_prayer_includes_the_detail() -> None:
    prayer = build_offline_prayer("guidance", detail="deciding whether to move")
    assert "deciding whether to move" in prayer["text"]


def test_offline_prayer_is_stable_for_the_same_topic() -> None:
    assert build_offline_prayer("hope")["text"] == build_offline_prayer("hope")["text"]


def test_offline_prayer_truncates_a_very_long_detail() -> None:
    prayer = build_offline_prayer("hope", detail="x" * 900)
    assert len(prayer["text"]) < 1200


# --- endpoints ---------------------------------------------------------


def test_topics_endpoint(client) -> None:
    body = client.get("/api/prayer/topics").get_json()
    assert len(body["topics"]) == len(PRAYER_TOPICS)
    assert body["disclaimer"]


def test_prayer_endpoint_hands_the_browser_a_prompt_and_a_fallback(client) -> None:
    body = client.post(
        "/api/prayer", json={"topic": "peace", "detail": "worried about my mum"}
    ).get_json()

    assert body["mode"] == "browser"
    assert "fallback" in body
    assert body["fallback"]["source"] == "offline"
    assert body["fallback"]["degraded"] is True
    assert body["prompt"]["system"]
    assert "worried about my mum" in body["prompt"]["messages"][-1]["content"]


def test_prayer_endpoint_honours_a_reference(client) -> None:
    body = client.post(
        "/api/prayer", json={"topic": "sorrow", "reference": "Psalm 34:18"}
    ).get_json()
    assert body["fallback"]["reference"] == "Psalm 34:18"
    assert "Psalm 34:18 says" in body["fallback"]["text"]


def test_prayer_endpoint_can_skip_ai_entirely(client) -> None:
    body = client.post(
        "/api/prayer", json={"topic": "hope", "generate": False}
    ).get_json()
    assert body["source"] == "offline"
    assert "prompt" not in body


def test_prayer_endpoint_rejects_an_unknown_topic_shape(client) -> None:
    response = client.post("/api/prayer", json={"topic": "x" * 100})
    assert response.status_code == 400


def test_prayer_endpoint_rejects_a_non_object_body(client) -> None:
    response = client.post("/api/prayer", json=["not", "an", "object"])
    assert response.status_code == 400
