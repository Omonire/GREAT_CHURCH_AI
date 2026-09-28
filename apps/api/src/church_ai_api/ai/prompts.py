"""Intent detection and prompt construction.

The Flask layer never calls a model by default. It recognises what the user
wants, pulls the real Scripture it needs, and assembles a well-formed prompt.
The browser then hands that prompt to Puter.js. If a server-side provider is
configured, the same prompt is sent there instead, so the two paths stay
interchangeable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from church_ai_api.ai.context import (
    BASE_PERSONA,
    ChatTurn,
    PreparedPrompt,
    SCRIPTURE_INTEGRITY,
)

# Ordered: the first match wins, so put specific patterns before broad ones.
_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "prayer",
        (
            r"\b(write|compose|draft|create|generate|give)\b[^.?]{0,40}\bprayer\b",
            r"\bprayer\b[^.?]{0,40}\b(for|about|on)\b",
            r"^\s*prayer\b",
        ),
    ),
    (
        "explain_verse",
        (
            r"\b(explain|what does|what do)\b[^.?]{0,40}\b(mean|say|verse|passage)\b",
            r"\b(explain)\b[^.?]{0,30}\b\w+\s*\d+:\d+",
            r"\bwhat does\b[^.?]{0,30}\b\w+\s*\d+:\d+",
        ),
    ),
    (
        "verses_about",
        (
            r"\b(verses?|scripture|passages?)\b[^.?]{0,30}\b(about|on|regarding|concerning)\b",
            r"\bbible (says|said)\b[^.?]{0,20}\babout\b",
            r"\b(what|which)\b[^.?]{0,20}\bverses?\b[^.?]{0,20}\babout\b",
        ),
    ),
    (
        "study",
        (
            r"\b(study|studies)\b",
            r"\b(summari[sz]e|key themes|outline|reflection questions|related scripture)\b",
            r"\bwalk me through\b",
            r"\bdevotional\b",
        ),
    ),
    (
        "define",
        (
            r"\b(what is|what are|define|meaning of|definition of)\b[^.?]{0,40}"
            r"\b(concept|doctrine|term|definition)\b",
        ),
    ),
    ("chat", (r".*",)),
)

_THEME_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("faith", (r"\bfaith\b",)),
    ("forgiveness", (r"\bforgiv", r"\bpardon")),
    ("love", (r"\blove\b",)),
    ("hope", (r"\bhope\b",)),
    ("peace", (r"\bpeace\b", r"\banxiet", r"\bworr")),
    ("wisdom", (r"\bwisdom\b", r"\bunderstand", r"\bdiscern")),
    ("strength", (r"\bstrength\b", r"\bstrengthen\b")),
    ("guidance", (r"\bguidance\b", r"\bdirection\b", r"\bdecision")),
    ("gratitude", (r"\bgratitude\b", r"\bthanks\w*\b", r"\bworship\b")),
    ("family", (r"\bfamily\b", r"\bmarriage\b", r"\bchildren\b")),
    ("relationships", (r"\brelationship\b", r"\bfriendship\b", r"\bforgive\b")),
    ("work", (r"\bwork\b", r"\bcareer\b", r"\bjob\b")),
    ("studies", (r"\bstud(y|ies|ent)\b", r"\bexam\b", r"\bschool\b")),
    ("prayer", (r"\bprayer\b", r"\bpray\b")),
)

_ACTION_PROMPTS: dict[str, tuple[str, str]] = {
    "explain": (
        "Explain this passage",
        "Walk through {reference} verse by verse. Explain what each part means, "
        "the original language where it matters, and how the surrounding context "
        "shapes it. Note anything a careful reader should watch out for.",
    ),
    "summarize": (
        "Summarise it",
        "Summarise {reference} clearly and briefly. Stay faithful to what the "
        "text actually says and do not add meaning it does not contain.",
    ),
    "themes": (
        "Key themes",
        "What are the key themes of {reference}? Name each theme and give the "
        "verses that develop it.",
    ),
    "reflect": (
        "Questions for reflection",
        "Give me thoughtful reflection questions for studying {reference}. Make "
        "them genuinely personal and open-ended, and explain what each question is "
        "trying to explore.",
    ),
    "outline": (
        "Sermon outline",
        "Build a preaching outline for {reference} for a Christian congregation. "
        "Give: a big idea in one sentence, then 3-5 points where each point states "
        "a truth from the text before any application, then a closing call to "
        "response. Every point must be traceable to the passage itself — do not "
        "import ideas the text does not contain.",
    ),
    "related": (
        "Related Scripture",
        "Which other passages connect to {reference}? Give the reference and one "
        "sentence on what the connection is, and be honest if a link is loose.",
    ),
}


def detect_intent(message: str) -> str:
    text = (message or "").lower()
    for name, patterns in _INTENTS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return name
    return "chat"


def detect_themes(message: str) -> list[str]:
    text = (message or "").lower()
    found: list[str] = []
    for theme, patterns in _THEME_HINTS:
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            found.append(theme)
    return found


def available_actions() -> list[dict[str, str]]:
    return [
        {"id": key, "label": label, "template": template}
        for key, (label, template) in _ACTION_PROMPTS.items()
    ]


def build_action_prompt(action: str, reference: str) -> str:
    entry = _ACTION_PROMPTS.get(action)
    if entry is None:
        raise ValueError(f"Unknown study action: {action}")
    return entry[1].format(reference=reference)


def prepare_chat(
    message: str,
    history: list[ChatTurn] | None = None,
    scripture: str | None = None,
    max_history: int = 12,
) -> PreparedPrompt:
    """Assemble the full prompt for a conversational turn."""
    system = BASE_PERSONA

    if scripture:
        system += (
            "\nThe user is currently reading this passage. Treat it as the primary "
            "text and stay anchored to it:\n\n" + scripture.strip() + "\n"
        )
    else:
        system += SCRIPTURE_INTEGRITY

    trimmed: list[ChatTurn] = list(history or [])[-max_history:] if max_history else []
    trimmed = [turn for turn in trimmed if turn.content and turn.content.strip()]

    return PreparedPrompt(
        system=system,
        messages=[*trimmed, ChatTurn(role="user", content=message.strip())],
        context={
            "intent": detect_intent(message),
            "themes": detect_themes(message),
            "has_scripture_context": bool(scripture),
        },
    )


def prepare_study(
    reference: str, action: str, scripture: str | None = None
) -> PreparedPrompt:
    """Assemble the prompt for a Bible study action on a specific passage."""
    system = BASE_PERSONA + SCRIPTURE_INTEGRITY
    if scripture:
        system += (
            "\nThe passage the user is studying is:\n\n"
            + scripture.strip()
            + "\n"
        )

    instruction = build_action_prompt(action, reference)
    return PreparedPrompt(
        system=system,
        messages=[ChatTurn(role="user", content=instruction)],
        context={"intent": "study", "action": action, "reference": reference},
    )


def prepare_sermon_outline(
    reference: str,
    scripture: str | None = None,
    title: str | None = None,
    notes: str | None = None,
) -> PreparedPrompt:
    """Assemble a preaching-outline prompt for a passage.

    Used by the sermon-notes page. The passage text is supplied by the caller so
    the model works from the bundled KJV rather than from memory.
    """
    system = (
        BASE_PERSONA
        + SCRIPTURE_INTEGRITY
        + "\nSermon rules:\n"
        "- You are drafting a scaffolding outline for a human preacher, not "
        "preaching. The preacher owns the message and the final wording.\n"
        "- Every point must be traceable to the passage. Never import a doctrine or "
        "theme the text does not contain.\n"
        "- Where a passage supports more than one reading, note it rather than "
        "picking one silently.\n"
        "- Application should be concrete and ordinary, not sentimental.\n"
    )
    if scripture:
        system += (
            "\nThe text you are working from is the King James Version of:\n\n"
            + scripture.strip()
            + "\n"
        )

    instruction = build_action_prompt("outline", reference)
    if title:
        instruction += f'\n\nThe preacher has chosen the working title "{title.strip()}".'
    if notes:
        instruction += (
            "\n\nThe preacher's own notes, which you should honour but not simply "
            "repeat:\n"
            + notes.strip()
        )

    return PreparedPrompt(
        system=system,
        messages=[ChatTurn(role="user", content=instruction)],
        context={"intent": "sermon", "action": "outline", "reference": reference},
    )


def prepare_prayer_draft(
    situation: str, scripture: str | None = None
) -> PreparedPrompt:
    """Assemble a prompt for a prayer written around a freeform situation.

    Used when the user describes what is on their heart rather than picking a
    topic from the list.
    """
    system = (
        BASE_PERSONA
        + "\nPrayer rules:\n"
        "- Write a prayer a person could pray out loud, addressed to God.\n"
        "- Speak to the person's specific situation without assuming details they "
        "did not give you.\n"
        "- Keep the tone sincere and grounded, not performative or ornate.\n"
        "- Do not claim the prayer came from God, and do not prophesy or predict "
        "what will happen.\n"
        "- Do not end by telling the person what God has already promised them.\n"
        "- Aim for roughly 120-180 words unless they ask for something shorter.\n"
    )
    if scripture:
        system += (
            "\nThe passage the user is reading, which you may draw on:\n\n"
            + scripture.strip()
            + "\n"
        )

    instruction = (
        "Write a prayer for someone who says: "
        + situation.strip()
        + "\n\nOpen honestly, speak to God about the situation they described, and "
        "close in a way that leaves room for God to act."
    )

    return PreparedPrompt(
        system=system,
        messages=[ChatTurn(role="user", content=instruction)],
        context={"intent": "prayer", "mode": "draft"},
    )


def prepare_prayer(topic: str, detail: str | None = None) -> PreparedPrompt:
    """Assemble the prompt for a generated prayer."""
    system = (
        BASE_PERSONA
        + "\nPrayer rules:\n"
        "- Write a prayer a person could pray out loud, addressed to God.\n"
        "- Keep the tone sincere and grounded, not performative or ornate.\n"
        "- Ground it in Scripture by naming a passage you are confident about.\n"
        "- Do not claim the prayer came from God, and do not prophesy.\n"
        "- Aim for roughly 120-180 words unless the user asks for something shorter.\n"
    )

    instruction = f"Write a prayer about {topic.strip()}."
    if detail and detail.strip():
        instruction += f" Keep this in mind: {detail.strip()}"

    return PreparedPrompt(
        system=system,
        messages=[ChatTurn(role="user", content=instruction)],
        context={"intent": "prayer", "topic": topic.strip()},
    )
