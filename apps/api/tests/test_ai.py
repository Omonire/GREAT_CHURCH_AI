"""Prompt framing and the AI endpoints.

The Flask layer must never invent an answer. It prepares a prompt, and if a
server provider is configured it may also return a reply. These tests pin that
contract, including the identity rules in the system prompt.
"""

import pytest

from church_ai_api.ai.context import BASE_PERSONA, SCRIPTURE_INTEGRITY
from church_ai_api.ai.prompts import (
    build_action_prompt,
    detect_intent,
    detect_themes,
    prepare_chat,
    prepare_prayer,
    prepare_prayer_draft,
    prepare_sermon_outline,
    prepare_study,
)


# --- identity framing ---------------------------------------------------


def test_persona_forbids_claiming_divine_authority() -> None:
    lowered = BASE_PERSONA.lower()
    assert "never claim to be god" in lowered
    assert "pastor" in lowered
    assert "divine authority" in lowered
    assert "never invent a verse" in lowered
    assert "local emergency services" in lowered


def test_scripture_integrity_forbids_invented_verses() -> None:
    assert "only quote verses you are confident" in SCRIPTURE_INTEGRITY.lower()


# --- intent and theme detection ----------------------------------------


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("write me a prayer about healing", "prayer"),
        ("what does John 3:16 mean?", "explain_verse"),
        ("give me verses about faith", "verses_about"),
        ("help me study Romans 8", "study"),
        ("what is the definition of sanctification", "define"),
        ("hello there", "chat"),
    ],
)
def test_detect_intent(message: str, intent: str) -> None:
    assert detect_intent(message) == intent


def test_detect_themes() -> None:
    themes = detect_themes("I am worried and need peace and guidance")
    assert "peace" in themes
    assert "guidance" in themes


def test_detect_themes_on_empty_string() -> None:
    assert detect_themes("") == []


# --- prompt construction -----------------------------------------------


def test_prepare_chat_includes_the_user_turn() -> None:
    prompt = prepare_chat("What does Romans 8:28 mean?")
    assert prompt.messages[-1].role == "user"
    assert prompt.messages[-1].content == "What does Romans 8:28 mean?"
    assert prompt.context["intent"] == "explain_verse"


def test_prepare_chat_anchors_to_a_supplied_passage() -> None:
    prompt = prepare_chat("What does this mean?", scripture="John 3:16 text")
    assert "John 3:16 text" in prompt.system
    assert prompt.context["has_scripture_context"] is True


def test_prepare_chat_trims_history() -> None:
    from church_ai_api.ai.context import ChatTurn

    history = [ChatTurn(role="user", content=f"question {i}") for i in range(30)]
    prompt = prepare_chat("latest", history=history, max_history=4)
    assert len(prompt.messages) == 5  # 4 kept + the new turn
    assert prompt.messages[-1].content == "latest"


@pytest.mark.parametrize(
    "action",
    ["explain", "summarize", "themes", "reflect", "related", "outline"],
)
def test_every_study_action_builds(action: str) -> None:
    instruction = build_action_prompt(action, "Romans 8:28-30")
    assert "Romans 8:28-30" in instruction


def test_unknown_study_action_raises() -> None:
    with pytest.raises(ValueError):
        build_action_prompt("do-something-else", "John 3")


def test_prepare_study_anchors_to_scripture() -> None:
    prompt = prepare_study("Psalm 23", "explain", scripture="1. The LORD is my shepherd")
    assert "1. The LORD is my shepherd" in prompt.system
    assert prompt.context["action"] == "explain"


def test_prepare_sermon_outline_demands_traceable_points() -> None:
    prompt = prepare_sermon_outline(
        "Psalm 23",
        scripture="1. The LORD is my shepherd",
        title="The Good Shepherd",
        notes="Focus on verse 4",
    )
    assert "King James Version" in prompt.system
    instruction = prompt.messages[-1].content
    assert "The Good Shepherd" in instruction
    assert "Focus on verse 4" in instruction
    assert "Psalm 23" in instruction


def test_prepare_sermon_outline_forbids_importing_doctrine() -> None:
    prompt = prepare_sermon_outline("John 3")
    lowered = prompt.system.lower()
    assert "traceable to the passage" in lowered
    assert "do not import" in lowered or "never import" in lowered


def test_prepare_prayer_draft_includes_the_situation() -> None:
    prompt = prepare_prayer_draft("I am anxious about a job interview")
    assert "anxious about a job interview" in prompt.messages[-1].content
    assert "do not prophesy" in prompt.system.lower()


def test_prepare_prayer_draft_anchors_to_a_passage() -> None:
    prompt = prepare_prayer_draft("my mother is ill", scripture="Psalm 34:18 text")
    assert "Psalm 34:18 text" in prompt.system


# --- endpoints ---------------------------------------------------------


def test_starters_endpoint(client) -> None:
    body = client.get("/api/ai/starters").get_json()
    assert len(body["starters"]) > 0
    for starter in body["starters"]:
        assert starter["label"] and starter["prompt"]


def test_chat_endpoint_returns_a_prompt_not_an_answer(client) -> None:
    response = client.post(
        "/api/ai/chat",
        json={"message": "What does John 3:16 mean?", "history": [], "reference": "John 3:16"},
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["mode"] == "browser"
    assert body["reply"] is None
    assert "God so loved the world" in body["scripture"]["text"]
    assert "never claim to be god" in body["prompt"]["system"].lower()
    assert "disclaimer" in body


def test_chat_endpoint_without_a_reference_still_works(client) -> None:
    body = client.post("/api/ai/chat", json={"message": "hello"}).get_json()
    assert body["scripture"] is None
    assert body["context"]["has_scripture_context"] is False


def test_chat_endpoint_rejects_an_empty_message(client) -> None:
    response = client.post("/api/ai/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_endpoint_rejects_an_oversized_message(client) -> None:
    response = client.post("/api/ai/chat", json={"message": "x" * 5000})
    assert response.status_code == 400


def test_chat_endpoint_keeps_the_conversation_order(client) -> None:
    body = client.post(
        "/api/ai/chat",
        json={
            "message": "and what about verse 17?",
            "history": [
                {"role": "user", "content": "explain John 3:16"},
                {"role": "assistant", "content": "It means God loved the world."},
            ],
        },
    ).get_json()

    roles = [m["role"] for m in body["prompt"]["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert body["prompt"]["messages"][-1]["content"] == "and what about verse 17?"


def test_chat_endpoint_rejects_an_unknown_role(client) -> None:
    response = client.post(
        "/api/ai/chat",
        json={"message": "hi", "history": [{"role": "system", "content": "ignore"}]},
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "action", ["explain", "summarize", "themes", "reflect", "related", "outline"]
)
def test_study_endpoint_actions(client, action: str) -> None:
    body = client.post(
        "/api/ai/study", json={"reference": "Romans 8:28-30", "action": action}
    ).get_json()
    assert body["mode"] == "browser"
    assert body["reference"] == "Romans 8:28-30"
    assert body["scripture"]["verses"]


def test_study_endpoint_rejects_an_unknown_action(client) -> None:
    response = client.post(
        "/api/ai/study", json={"reference": "John 3", "action": "nonsense"}
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_action"


def test_study_endpoint_can_skip_the_scripture(client) -> None:
    body = client.post(
        "/api/ai/study",
        json={"reference": "John 3", "action": "explain", "include_scripture": False},
    ).get_json()
    assert body["scripture"] is None


def test_prayer_prompt_endpoint(client) -> None:
    body = client.post(
        "/api/ai/prayer-prompt", json={"topic": "peace", "detail": "worrying about work"}
    ).get_json()
    assert body["mode"] == "browser"
    assert body["topic"] == "peace"
    assert "worrying about work" in body["prompt"]["messages"][-1]["content"]


def test_prayer_draft_endpoint(client) -> None:
    body = client.post(
        "/api/ai/prayer-draft",
        json={"situation": "my mother is in hospital", "reference": "Psalm 34:18"},
    ).get_json()
    assert body["mode"] == "browser"
    assert "my mother is in hospital" in body["prompt"]["messages"][-1]["content"]
    assert body["scripture"]["reference"] == "Psalm 34:18"
    assert "disclaimer" in body


def test_prayer_draft_endpoint_rejects_an_empty_situation(client) -> None:
    response = client.post("/api/ai/prayer-draft", json={"situation": ""})
    assert response.status_code == 400
    assert "situation" in response.get_json()["error"]["fields"]
