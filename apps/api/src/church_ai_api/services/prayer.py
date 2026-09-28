"""Prayer topics and the offline, clearly-labelled fallback text.

Prayer generation is genuinely AI-driven when a model is available. When no
model is reachable the service returns a clearly-labelled assembled prayer
built from public-domain KJV text. The response always says which one it is, so
a template is never presented as a generated prayer.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from church_ai_api.bible.corpus import (
    CorpusEmpty,
    CorpusUnavailable,
    get_corpus,
)
from church_ai_api.bible.reference import parse_reference
from church_ai_api.bible.service import ScriptureError, get_scripture_service
from church_ai_api.bible.verses import CATALOGUE, entries_by_theme

PRAYER_DISCLAIMER = (
    "This is AI-generated assistance. It is a starting point for your own "
    "prayer, not something to read as if it came from a prophet or from God."
)


@dataclass(frozen=True, slots=True)
class PrayerTopic:
    id: str
    label: str
    description: str
    prompt_hint: str


PRAYER_TOPICS: tuple[PrayerTopic, ...] = (
    PrayerTopic(
        "gratitude",
        "Gratitude",
        "Thanksgiving for ordinary and unnoticed gifts.",
        "Give thanks with warmth and specificity, not a generic list.",
    ),
    PrayerTopic(
        "guidance",
        "Guidance",
        "Asking for direction when a decision is hard to see.",
        "Acknowledge the difficulty of the decision honestly.",
    ),
    PrayerTopic(
        "wisdom",
        "Wisdom",
        "Asking for a clear mind and discernment.",
        "Be honest about how little clarity there often is.",
    ),
    PrayerTopic(
        "peace",
        "Peace",
        "For anxiety, unrest, and a troubled mind.",
        "Do not dismiss the person's worry; bring it honestly to God.",
    ),
    PrayerTopic(
        "strength",
        "Strength",
        "For endurance through something long and tiring.",
        "Steady and sustaining rather than triumphant.",
    ),
    PrayerTopic(
        "family",
        "Family",
        "For those you love, and for the people who are difficult.",
        "Include grace for the people who are hard to love.",
    ),
    PrayerTopic(
        "studies",
        "Studies",
        "For exams, learning, and seasons of work.",
        "Tied to diligence and humility rather than luck.",
    ),
    PrayerTopic(
        "work",
        "Work",
        "For a job, a calling, and using your time well.",
        "Respectful of ordinary working life.",
    ),
    PrayerTopic(
        "relationships",
        "Relationships",
        "For friendship, conflict, and repair.",
        "Include patience and honest speech.",
    ),
    PrayerTopic(
        "forgiveness",
        "Forgiveness",
        "Forgiving someone, and being forgiven.",
        "Neither rushes the other person nor excuses harm.",
    ),
    PrayerTopic(
        "sorrow",
        "Sorrow",
        "For grief, loss, and seasons of grief.",
        "Tender and unhurried. Never explain someone's pain back to them.",
    ),
    PrayerTopic(
        "hope",
        "Hope",
        "For waiting, and for what has not happened yet.",
        "Honest about the wait rather than falsely cheerful.",
    ),
)

TOPIC_INDEX: dict[str, PrayerTopic] = {topic.id: topic for topic in PRAYER_TOPICS}

# Bundled verses whose theme matches a topic, used by the offline fallback.
_THEME_BY_TOPIC: dict[str, str] = {
    "gratitude": "gratitude",
    "guidance": "guidance",
    "wisdom": "wisdom",
    "peace": "peace",
    "strength": "strength",
    "family": "family",
    "studies": "studies",
    "work": "work",
    "relationships": "relationships",
    "forgiveness": "relationships",
    "sorrow": "comfort",
    "hope": "hope",
}

# A representative passage per topic, shown next to the label in the picker.
_TOPIC_SCRIPTURE: dict[str, str] = {
    "gratitude": "Psalm 100:4",
    "guidance": "Psalm 32:8",
    "wisdom": "James 1:5",
    "peace": "Philippians 4:6-7",
    "strength": "Isaiah 40:31",
    "family": "Psalm 127:1",
    "studies": "Proverbs 16:3",
    "work": "Colossians 3:23",
    "relationships": "Ephesians 4:32",
    "forgiveness": "Psalm 103:12",
    "sorrow": "Psalm 34:18",
    "hope": "Romans 15:13",
}

_OPENERS: tuple[str, ...] = (
    "Father, thank you that I can bring this to you honestly.",
    "God, I come to you with a heavy heart and a need for your help.",
    "Lord, I do not have the words I want, so I will simply start here.",
    "Father, I bring you my questions as honestly as I know how.",
)

_BODIES: dict[str, str] = {
    "gratitude": (
        "Thank you for what I can name and for what I cannot. For the people who "
        "stayed, for the ordinary morning, for a body that carried me through the "
        "week. Let me notice more of what is already here."
    ),
    "guidance": (
        "I do not see the next step clearly. Give me enough courage to take the "
        "step in front of me, and enough honesty to know when I am choosing from "
        "fear rather than faith."
    ),
    "wisdom": (
        "Give me a clear mind and a humble one. Let me be slow to conclude and "
        "willing to be corrected, and let me hold my opinions loosely enough to "
        "change them."
    ),
    "peace": (
        "I do not need to pretend I am not worried. Take the worry I cannot put "
        "down, and give me a peace that is real and not just a feeling I am "
        "performing."
    ),
    "strength": (
        "This has been long, and I am tired. I do not ask for the strength I "
        "imagined I would have. Give me what I actually need to get through today."
    ),
    "family": (
        "Bless the people I love, including the ones I find difficult. Give me "
        "patience that lasts, and make me safe to love without keeping score."
    ),
    "studies": (
        "Give me diligence rather than luck. Keep me honest about what I do not "
        "understand yet, and let me learn with humility instead of anxiety."
    ),
    "work": (
        "Let me do honest work and let it be enough. Free me from measuring my "
        "worth by what I produce, and use whatever I am doing for someone else."
    ),
    "relationships": (
        "Give me words that are true and words that are kind. Make me quick to "
        "listen and slow to accuse, and teach me to repair what has been broken."
    ),
    "forgiveness": (
        "Teach me what forgiveness actually costs and what it actually gives. "
        "Free me from the need to keep this wound open, and give me grace for the "
        "person who hurt me without pretending it did not happen."
    ),
    "sorrow": (
        "Come close to me in this. I do not understand it, and I do not want to be "
        "told I should. Just stay with me, and let me grieve honestly."
    ),
    "hope": (
        "I am waiting for something I cannot see yet. Keep me faithful in the "
        "waiting, and let me hold onto your promise without pretending I understand "
        "the timing."
    ),
}

_CLOSERS: tuple[str, ...] = (
    "Whatever comes next, I would rather walk it with you than apart from you. "
    "In Jesus' name, amen.",
    "Thank you for hearing me. I will try to live like someone who has been "
    "heard. In Jesus' name, amen.",
    "I lay this down, not because I have it together, but because you do. "
    "In Jesus' name, amen.",
)

_DEFAULT_TOPIC = PrayerTopic(
    "reflection",
    "General Reflection",
    "An open prayer for whatever is on your heart.",
    "",
)


def list_topics() -> list[dict[str, str]]:
    return [
        {
            "id": topic.id,
            "slug": topic.id,
            "label": topic.label,
            "description": topic.description,
            "hint": topic.prompt_hint,
            "scripture": _TOPIC_SCRIPTURE.get(topic.id, ""),
        }
        for topic in PRAYER_TOPICS
    ]


def get_topic(topic_id: str) -> PrayerTopic:
    key = (topic_id or "").strip().lower()
    return TOPIC_INDEX.get(key, _DEFAULT_TOPIC)


def _seed_for(topic_id: str) -> random.Random:
    """Stable per-topic ordering so a refresh does not reshuffle the text."""
    return random.Random(f"great-church-ai::{topic_id}")


def _verse_text(entry) -> str:
    """Resolve real KJV text for a catalogue entry."""
    reference = parse_reference(entry.reference)
    if reference is None:
        return ""
    try:
        return get_corpus().text_for(
            reference.book, reference.chapter, reference.all_verses[0]
        )
    except (CorpusEmpty, CorpusUnavailable):
        return ""


def resolve_anchor(reference: str | None) -> dict | None:
    """Look up a user-supplied passage so the prayer can quote real text.

    Returns ``None`` when the reference cannot be read. Nothing is ever
    substituted or invented here.
    """
    candidate = (reference or "").strip()
    if not candidate:
        return None

    parsed = parse_reference(candidate)
    if parsed is None:
        return None

    try:
        return get_scripture_service().get_parsed_reference(parsed)
    except ScriptureError:
        return None


def build_offline_prayer(
    topic_id: str,
    detail: str | None = None,
    reference: str | None = None,
) -> dict:
    """Assemble a labelled offline prayer from public-domain text."""
    topic = get_topic(topic_id)
    theme = _THEME_BY_TOPIC.get(topic.id, "")

    candidates = entries_by_theme(theme) or list(CATALOGUE)
    rng = _seed_for(topic.id)
    entry = candidates[rng.randrange(len(candidates))]

    opener = _OPENERS[rng.randrange(len(_OPENERS))]
    closer = _CLOSERS[rng.randrange(len(_CLOSERS))]
    body = _BODIES.get(
        topic.id,
        "Let me bring you whatever is on my heart today, honestly and without "
        "pretense, and let you make of it what you intend.",
    )

    detail_line = ""
    if detail and detail.strip():
        cleaned = " ".join(detail.strip().split())
        if len(cleaned) > 220:
            cleaned = cleaned[:217].rstrip() + "..."
        detail_line = f"\n\nAnd Lord, remember this: {cleaned}"

    # A passage the user named wins. Otherwise fall back to the themed verse.
    anchor = resolve_anchor(reference)
    if anchor:
        anchor_scripture = {
            "reference": anchor["reference"],
            "text": anchor["text"],
            "translation": anchor["translation"],
        }
        scripture_line = (
            f'\n\n{anchor["reference"]} says, “{anchor["text"]}”'
        )
    else:
        quoted = _verse_text(entry)
        anchor_scripture = (
            {"reference": entry.reference, "text": quoted, "translation": "KJV"}
            if quoted
            else None
        )
        scripture_line = f'\n\n{entry.reference} says, “{quoted}”' if quoted else ""

    text = f"{opener}\n\n{body}{detail_line}{scripture_line}\n\n{closer}"

    payload = {
        "topic": topic.label,
        "text": text,
        "source": "offline",
        "degraded": True,
        "disclaimer": (
            "No AI model was available, so this is a short assembled prayer "
            "using public-domain King James Version text, not a generated prayer. "
            "Connect an AI model for a prayer written to your situation."
        ),
    }
    if anchor_scripture:
        payload["anchor_scripture"] = anchor_scripture
        payload["reference"] = anchor_scripture["reference"]
    if reference and not anchor:
        payload["warning"] = (
            f"The reference “{reference.strip()}” could not be read, so the themed "
            "verse was used instead."
        )
    return payload
