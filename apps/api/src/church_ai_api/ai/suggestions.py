"""Starter prompts shown in the chat UI.

These are starting points for the user, not canned answers. Nothing here is a
response: every one of them produces a real model call when the user submits.
"""

from __future__ import annotations

STARTER_PROMPTS: tuple[dict[str, str], ...] = (
    {
        "id": "hebrews-throne",
        "label": "Hebrews 4 — the throne of grace",
        "prompt": "What does Hebrews 4 say about the throne of grace?",
    },
    {
        "id": "romans-8",
        "label": "Study Romans 8",
        "prompt": "Help me study Romans 8. What is the main argument, and how does it build?",
    },
    {
        "id": "forgiveness",
        "label": "Forgiveness",
        "prompt": "What does the Bible say about forgiveness?",
    },
    {
        "id": "faith-verse",
        "label": "Verses about faith",
        "prompt": "Give me Bible verses about faith, and explain what they have in common.",
    },
    {
        "id": "difficult-passage",
        "label": "Understanding a hard passage",
        "prompt": "Explain the Book of Ecclesiastes in modern English. What is it actually saying?",
    },
    {
        "id": "disagreement",
        "label": "A disputed passage",
        "prompt": "Is Hell eternal punishment or annihilation? Show me the main passages on both sides.",
    },
    {
        "id": "prayer-guidance",
        "label": "A prayer for guidance",
        "prompt": "Help me create a prayer for a decision I need to make.",
    },
    {
        "id": "difficult-concept",
        "label": "Explaining a concept",
        "prompt": "Explain the concept of sanctification in plain language.",
    },
)
