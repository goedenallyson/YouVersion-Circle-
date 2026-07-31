"""Pydantic schemas — the stable contract between layers and clients."""
from __future__ import annotations

from pydantic import BaseModel, Field


class VerseRef(BaseModel):
    translation: str
    book: str
    chapter: int
    verse: int

    @property
    def citation(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse} ({self.translation})"


class ScriptureChunk(BaseModel):
    """A retrievable unit of scripture (one or more verses)."""

    id: str
    text: str
    ref: VerseRef
    end_verse: int | None = None
    score: float | None = None

    @property
    def citation(self) -> str:
        if self.end_verse and self.end_verse != self.ref.verse:
            return (
                f"{self.ref.book} {self.ref.chapter}:"
                f"{self.ref.verse}-{self.end_verse} ({self.ref.translation})"
            )
        return self.ref.citation


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    translation: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=25)


class Citation(BaseModel):
    citation: str
    text: str
    score: float | None = None


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    grounded: bool = Field(
        ..., description="True if the answer is supported by retrieved scripture."
    )


class SearchResponse(BaseModel):
    query: str
    results: list[ScriptureChunk]


class MomentRequest(BaseModel):
    type: str = Field(..., description="IDE moment type, e.g. test_failed")
    minutes_in_state: int = Field(default=0, ge=0)
    local_hour: int | None = Field(default=None, ge=0, le=23)
    consecutive_failures: int = Field(default=0, ge=0)
    language: str = "en"
    translation: str | None = None
    tags: list[str] = Field(default_factory=list)


class MomentResponse(BaseModel):
    type: str
    theme: str
    verse: Citation
    reflection: str
    model: str
    alternatives: list[Citation]


# ---------------------------------------------------------------------------
# YouVersion Circle — Verse-of-the-Day learning loop
#
# Loop: daily verse -> tiny engagement signal -> group pulse unlocks ->
# Gloo AI learns themes -> tomorrow's recommendation improves.
# ---------------------------------------------------------------------------


class VerseOfDay(BaseModel):
    date: str = Field(..., description="ISO date (YYYY-MM-DD) this verse is for.")
    citation: str
    text: str
    theme: str = Field(..., description="Pastoral theme driving today's pick.")
    translation: str
    source: str = Field(
        ..., description="youversion | local — where the text came from."
    )
    verse_count: int = Field(
        default=1, ge=1, description="Number of verses in the passage (1–3)."
    )
    selection_source: str = Field(
        default="verse-of-day",
        description=(
            "verse-of-day = predetermined daily content; "
            "recommended-for-group = adaptive from prior group engagement."
        ),
    )
    selection_label: str = Field(
        default="Verse of the Day",
        description="Human label distinguishing predetermined vs adaptive content.",
    )
    group_streak: int = Field(default=0, ge=0)
    unlocked: bool = Field(
        default=False, description="True once the user has given a signal today."
    )


class EngagementSignal(BaseModel):
    """The tiny, low-friction input that drives the learning loop.

    Intentionally small: a reaction, an optional highlighted phrase, one word,
    and a life-context tag. No free-form essays, no PII.
    """

    group_id: str = Field(default="demo", max_length=64)
    member_id: str | None = Field(
        default=None,
        max_length=64,
        description="Mock/local member identity; one response per member/day.",
    )
    username: str | None = Field(
        default=None,
        max_length=64,
        description="Display name shown to the group (responses are NOT anonymous).",
    )
    date: str | None = Field(
        default=None, description="ISO date; defaults to today (UTC)."
    )
    reaction: str | None = Field(
        default=None, description="Emoji/short reaction, e.g. \U0001f64f."
    )
    highlight: str | None = Field(
        default=None, max_length=200, description="Phrase highlighted in the verse."
    )
    word: str | None = Field(
        default=None, max_length=40, description="One-word reflection."
    )
    tag: str | None = Field(
        default=None,
        max_length=40,
        description="Life-context tag, e.g. Work | Anxiety | Family | Rest.",
    )
    reflection: str | None = Field(
        default=None,
        max_length=500,
        description="Short free-text reflection (kept brief; no essays).",
    )


class Member(BaseModel):
    """A mock/local member persona for the prototype (no real accounts)."""

    id: str
    name: str
    avatar: str | None = Field(default=None, description="Emoji/initial avatar.")


class GroupSynthesis(BaseModel):
    """AI/fallback synthesis of a circle's shared responses for a date."""

    needs: list[str] = Field(default_factory=list)
    praises: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    summary: str = ""
    headline: str = Field(
        default="",
        description=(
            "Adaptive one-liner, e.g. 'Anxiety was the group’s top need today' or "
            "'Gratitude was the group’s top praise today'."
        ),
    )
    classification: str = Field(
        default="shared theme",
        description=(
            "top need | top praise | shared theme | common reflection | "
            "strongest encouragement | most selected emotion"
        ),
    )
    confidence: str = Field(
        default="low",
        description="low | medium | high — group-level weighting, not one voice.",
    )
    response_count: int = Field(default=0, ge=0)
    model: str = Field(default="circle-fallback", description="gloo-ai-studio | circle-fallback")
    provider: str = Field(default="fallback", description="gloo | fallback")


class PulseEntry(BaseModel):
    """One member's response, attributed (responses are NOT anonymous).

    Only fields the member actually used that day are populated; the client
    should not render empty fields.
    """

    member_id: str | None = None
    username: str | None = None
    reaction: str | None = None
    highlight: str | None = None
    word: str | None = None
    tag: str | None = None
    reflection: str | None = None


class GroupPulse(BaseModel):
    """Named (non-anonymous), aggregated view of the circle's responses."""

    group_id: str
    group_name: str = Field(default="Your circle", description="Display name shown atop the pulse.")
    date: str
    unlocked: bool
    total_responses: int
    top_tag: str | None = None
    top_tag_pct: int = Field(default=0, ge=0, le=100)
    top_word: str | None = None
    top_highlight: str | None = None
    highlight_count: int = 0
    reflection_count: int = 0
    reactions: dict[str, int] = Field(default_factory=dict)
    entries: list[PulseEntry] = Field(default_factory=list)
    synthesis: GroupSynthesis | None = Field(
        default=None,
        description="Group-level synthesis of needs/praises/themes (unlocked only).",
    )


class SignalResponse(BaseModel):
    accepted: bool
    verse: VerseOfDay
    pulse: GroupPulse


class SignalStrength(BaseModel):
    """How much a collected signal is weighted for recommendations."""

    signal: str = Field(..., description="Signal name, e.g. 'written reflection'.")
    strength: str = Field(..., description="strong | moderate | weak | context")
    present: bool = Field(default=False, description="Was this signal present today?")
    note: str = Field(default="")


class RecommendationPlan(BaseModel):
    """Transparent, structured record of how the next passage was chosen.

    Surfaced in Demo Mode so an evaluator can see the AI-learning workflow and
    the safeguards that were applied. Stored as the recommendation reason for
    debugging/eval.
    """

    workflow: list[str] = Field(
        default_factory=list, description="Ordered steps that produced the pick."
    )
    signals: list[SignalStrength] = Field(default_factory=list)
    strongest_themes: list[str] = Field(default_factory=list)
    confidence: str = Field(default="low", description="low | medium | high")
    candidate_references: list[str] = Field(default_factory=list)
    selected_reference: str = ""
    rejected_candidates: list[str] = Field(default_factory=list)
    safeguards_applied: list[str] = Field(default_factory=list)
    reason: str = ""


class TomorrowRecommendation(BaseModel):
    date: str = Field(..., description="ISO date the recommendation is for.")
    based_on_date: str
    theme: str = Field(..., description="Theme tomorrow's verse is tuned toward.")
    citation: str
    text: str
    translation: str
    source: str
    explanation: str = Field(
        ..., description="Transparent, human-readable why-this-verse rationale."
    )
    model: str = Field(..., description="Which engine produced the framing/pick.")
    signals: list[str] = Field(
        default_factory=list, description="Bullet summary of today's signals."
    )
    engagement_level: str = Field(
        default="none",
        description="none | low | medium | high — how active the group was.",
    )
    verse_count: int = Field(default=1, ge=1)
    selection_source: str = Field(
        default="recommended-for-group",
        description="Always adaptive: tomorrow is 'Recommended for Your Group'.",
    )
    selection_label: str = Field(default="Recommended for Your Group")
    recommendation_reason: str = Field(
        default="",
        description="Stored reason string for debugging/eval (why this passage).",
    )
    rejected_candidates: list[str] = Field(
        default_factory=list,
        description="Other candidate citations not chosen (repetition/length rules).",
    )
    plan: RecommendationPlan | None = Field(
        default=None,
        description="Structured recommendation workflow + signal weighting (Demo Mode).",
    )


class MembersResponse(BaseModel):
    group_id: str
    members: list[Member]


class HealthResponse(BaseModel):
    status: str
    environment: str
    bible_provider: str
    gloo_configured: bool
    index_size: int
