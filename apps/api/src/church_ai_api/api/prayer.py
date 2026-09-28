"""Prayer endpoints.

Prayer generation is genuinely AI-driven when a model is reachable. When none
is, the response says so and carries a clearly-labelled offline prayer built
from public-domain text. A template is never presented as a generated prayer.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from church_ai_api.ai.prompts import prepare_prayer
from church_ai_api.ai.provider import ProviderError, ServerProvider
from church_ai_api.schemas.requests import PrayerRequest
from church_ai_api.services.prayer import (
    PRAYER_DISCLAIMER,
    build_offline_prayer,
    get_topic,
    list_topics,
)

logger = logging.getLogger(__name__)

blueprint = Blueprint("prayer", __name__)


def _error(code: str, message: str, status: int):
    return jsonify({"error": {"code": code, "message": message, "status": status}}), status


@blueprint.get("/api/prayer/topics")
def topics():
    return jsonify(topics=list_topics(), disclaimer=PRAYER_DISCLAIMER)


@blueprint.post("/api/prayer")
def generate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("invalid_request", "A prayer topic is required.", 400)

    try:
        payload = PrayerRequest.model_validate(data)
    except ValidationError:
        return _error(
            "invalid_request",
            "That prayer request was not valid. Check the topic and try again.",
            400,
        )

    topic = get_topic(payload.topic)
    provider = ServerProvider()

    offline = lambda: build_offline_prayer(
        topic.id, payload.detail, payload.reference
    )

    # Explicitly opt out of AI: hand back the assembled prayer straight away.
    if not payload.generate:
        return jsonify(
            {
                **offline(),
                "topic": topic.label,
                "topic_id": topic.id,
                "disclaimer": PRAYER_DISCLAIMER,
            }
        )

    if provider.enabled:
        prompt = prepare_prayer(topic.id, payload.detail)
        try:
            text = provider.complete(prompt)
        except ProviderError as error:
            logger.warning("Prayer generation fell back to offline text: %s", error)
            return jsonify(
                {
                    **offline(),
                    "topic": topic.label,
                    "topic_id": topic.id,
                    "disclaimer": PRAYER_DISCLAIMER,
                    "warning": (
                        "The AI provider could not be reached, so this is the "
                        "assembled offline prayer instead."
                    ),
                }
            )

        return jsonify(
            {
                "topic": topic.label,
                "topic_id": topic.id,
                "text": text,
                "source": "ai",
                "degraded": False,
                "disclaimer": PRAYER_DISCLAIMER,
            }
        )

    # No server-side model configured. Prepare the prompt for the browser and
    # include the offline prayer so the UI always has something honest to show.
    prompt = prepare_prayer(topic.id, payload.detail)
    return jsonify(
        {
            "topic": topic.label,
            "topic_id": topic.id,
            "prompt": prompt.as_payload(),
            "mode": "browser",
            "fallback": offline(),
            "disclaimer": PRAYER_DISCLAIMER,
        }
    )
