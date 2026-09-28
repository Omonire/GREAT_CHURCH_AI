"""Prompt construction, identity framing, and optional server-side generation."""

from church_ai_api.ai.context import ChatTurn, PreparedPrompt
from church_ai_api.ai.prompts import (
    available_actions,
    build_action_prompt,
    detect_intent,
    detect_themes,
    prepare_chat,
    prepare_prayer,
    prepare_study,
)
from church_ai_api.ai.provider import ProviderError, ServerProvider
from church_ai_api.ai.suggestions import STARTER_PROMPTS

__all__ = [
    "ChatTurn",
    "PreparedPrompt",
    "ProviderError",
    "STARTER_PROMPTS",
    "ServerProvider",
    "available_actions",
    "build_action_prompt",
    "detect_intent",
    "detect_themes",
    "prepare_chat",
    "prepare_prayer",
    "prepare_study",
]
