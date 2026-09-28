"""Sermon note templates and clearly-labelled demonstration content.

Nothing in here is a real sermon from a real church. Every demonstration note
carries ``demo: True`` and the API says so in the response, so it can never be
mistaken for a recording of an actual church service.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SermonNote:
    id: str
    title: str
    passage: str
    theme: str
    summary: str
    key_points: tuple[str, ...]
    reflection_questions: tuple[str, ...]
    related_scripture: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "passage": self.passage,
            "theme": self.theme,
            "summary": self.summary,
            "key_points": list(self.key_points),
            "reflection_questions": list(self.reflection_questions),
            "related_scripture": list(self.related_scripture),
            "demo": True,
        }


DEMO_NOTE_DISCLAIMER = (
    "Demonstration content. This note was written to show the layout and is not "
    "a sermon from a real church, congregation, or preacher."
)


OUTLINE_DISCLAIMER = (
    "An outline is a drafting scaffold, not a sermon and not the Word of God. "
    "Check every point against the text and preach it in your own voice."
)


DEMO_NOTES: tuple[SermonNote, ...] = (
    SermonNote(
        id="demo-waiting",
        title="Learning to Wait Well",
        passage="Habakkuk 2:20",
        theme="Patience",
        summary=(
            "Habakkuk asks God a blunt question: how long should a person wait for "
            "justice? The chapter answers that the vision is still coming, and that "
            "the one who waits is not wasting time. The note walks through the "
            "difference between waiting passively and waiting awake."
        ),
        key_points=(
            "Honest questions to God are not a lack of faith; they are part of it.",
            "Waiting is active. The prophet stays engaged rather than checking whether he is heard.",
            "Certainty about the outcome can arrive before the outcome does.",
        ),
        reflection_questions=(
            "What are you currently waiting for, and what would it mean to wait awake rather than impatient?",
            "Where has God already answered a question you have since forgotten to ask?",
            "What would change this week if you trusted that the outcome is already decided?",
        ),
        related_scripture=("Romans 8:25", "Lamentations 3:25-26", "Psalm 27:1"),
    ),
    SermonNote(
        id="demo-joy",
        title="The Command to Rejoice Is Reasonable",
        passage="Nehemiah 8:17",
        theme="Joy",
        summary=(
            "After rebuilding the wall and finishing the reading of the law, the "
            "people are told to go and enjoy the LORD. The note covers why Scripture "
            "treats joy as a practice rather than a mood, and what that looks like on "
            "a hard week."
        ),
        key_points=(
            "Joy in Scripture is sometimes a command, which makes it a practice rather than a feeling.",
            "The people who rejoiced had just been told about their own failure, and rejoiced anyway.",
            "Delight in God is not a substitute for grief, but it can exist alongside it.",
        ),
        reflection_questions=(
            "When did you last take joy as something to practise rather than something to wait for?",
            "Is there a place where you are confusing sadness with faithfulness?",
            "What would it look like to deliberately enjoy one good thing this week?",
        ),
        related_scripture=("Psalm 16:11", "1 Peter 1:6-7", "Nehemiah 8:10"),
    ),
    SermonNote(
        id="demo-conversion",
        title="When God Changes the Plan",
        passage="Jeremiah 29:11-14",
        theme="Calling",
        summary=(
            "Written to people in exile whose expected future had collapsed, this "
            "passage refuses to promise an easy return. The note explores the gap "
            "between what was asked for and what was actually given, and why that gap "
            "is sometimes where the growth is."
        ),
        key_points=(
            "The plans people have for their own future are not the same as God's plan for their good.",
            "Peace in a hard place can be found before the hard place is resolved.",
            "Being asked to seek and to pray is itself an invitation to relationship.",
        ),
        reflection_questions=(
            "What plan have you had to let go of, and did you let it go resentfully or peacefully?",
            "Where might God's plan for your good differ from the one you would have chosen?",
            "What would you ask for today if you trusted that you would be heard?",
        ),
        related_scripture=("Psalm 139:23-24", "Romans 8:28", "Isaiah 55:8-9"),
    ),
    SermonNote(
        id="demo-unity",
        title="One Room, One Table",
        passage="Acts 2:42-47",
        theme="Community",
        summary=(
            "A short teaching on the shape of the early church: teaching, fellowship, "
            "bread, and prayer, held together by genuine sharing. The note asks what "
            "it means to have a community that notices when someone is missing."
        ),
        key_points=(
            "The four practices in this passage are ordinary, repeatable habits rather than dramatic events.",
            "Sharing resources was structural, not sentimental.",
            "Attendance is not the same as belonging, and this passage assumes both.",
        ),
        reflection_questions=(
            "Who in your church would notice if you stopped showing up?",
            "What practical habit of sharing does this passage describe that your community does not have?",
            "What would it take for your church to notice a person who quietly left?",
        ),
        related_scripture=("Romans 12:15-16", "Galatians 6:10", "1 John 3:18"),
    ),
)

NOTE_INDEX: dict[str, SermonNote] = {note.id: note for note in DEMO_NOTES}


def list_notes() -> list[dict]:
    return [note.as_dict() for note in DEMO_NOTES]


def get_note(note_id: str) -> SermonNote | None:
    return NOTE_INDEX.get((note_id or "").strip().lower())


def blank_note_template() -> dict:
    """An empty structure the UI can prefill for the user's own notes."""
    return {
        "id": None,
        "title": "",
        "passage": "",
        "theme": "",
        "summary": "",
        "key_points": [],
        "reflection_questions": [],
        "related_scripture": [],
        "demo": False,
        "editable": True,
    }
