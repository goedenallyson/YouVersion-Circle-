"""HTTP routes for the YouVersion Circle Scripture demo."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.deps import get_engine, get_circle_engine
from app.models.schemas import (
    EngagementSignal,
    GroupPulse,
    HealthResponse,
    MembersResponse,
    SearchResponse,
    SignalResponse,
    TomorrowRecommendation,
    VerseOfDay,
)
from app.providers.gloo import GlooLLMProvider
from app.rag.engine import RagEngine
from app.rag.circle import CircleEngine

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings),
    engine: RagEngine = Depends(get_engine),
) -> HealthResponse:
    gloo = isinstance(engine.llm, GlooLLMProvider) and engine.llm.configured
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        bible_provider=settings.bible_provider,
        gloo_configured=bool(gloo),
        index_size=engine.store.size,
    )


# ---------------------------------------------------------------------------
# YouVersion Circle — Verse-of-the-Day learning loop
# ---------------------------------------------------------------------------


@router.get("/circle/verse-of-day", response_model=VerseOfDay)
def verse_of_day(
    group_id: str = "demo",
    date: str | None = None,
    circle: CircleEngine = Depends(get_circle_engine),
) -> VerseOfDay:
    """Today's verse for the group. `unlocked` reflects whether the user has
    already given a signal today (which reveals the group pulse)."""
    try:
        return circle.verse_of_day(group_id=group_id, date_iso=date)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/circle/signal", response_model=SignalResponse)
def submit_signal(
    signal: EngagementSignal,
    circle: CircleEngine = Depends(get_circle_engine),
) -> SignalResponse:
    """Submit a tiny engagement signal (reaction / highlight / word / tag).
    This unlocks the group pulse and feeds tomorrow's recommendation."""
    try:
        verse, pulse = circle.submit_signal(signal)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return SignalResponse(accepted=True, verse=verse, pulse=pulse)


@router.get("/circle/members", response_model=MembersResponse)
def circle_members(
    group_id: str = "demo",
    circle: CircleEngine = Depends(get_circle_engine),
) -> MembersResponse:
    """Seeded mock member personas for the prototype (no real accounts)."""
    return MembersResponse(group_id=group_id, members=circle.members())


@router.get("/circle/config")
def circle_config(
    group_id: str = "demo",
    circle: CircleEngine = Depends(get_circle_engine),
) -> dict:
    """Client bootstrap: approved emoji set + group name. Keeps the curated
    emoji list authoritative on the server (no unrestricted library)."""
    return {
        "group_id": group_id,
        "group_name": circle.group_name(),
        "approved_emoji": circle.approved_emoji(),
        "privacy_notice": (
            "Responses are shared with your group and are not anonymous. "
            "Group-level insights are AI-generated."
        ),
    }


@router.get("/circle/pulse", response_model=GroupPulse)
def group_pulse(
    group_id: str = "demo",
    date: str | None = None,
    circle: CircleEngine = Depends(get_circle_engine),
) -> GroupPulse:
    """The circle's named (non-anonymous), aggregated responses. Locked until
    the user has given at least one signal for the date."""
    return circle.group_pulse(group_id=group_id, date_iso=date)


@router.get("/circle/tomorrow", response_model=TomorrowRecommendation)
def tomorrow(
    group_id: str = "demo",
    date: str | None = None,
    circle: CircleEngine = Depends(get_circle_engine),
) -> TomorrowRecommendation:
    """Tomorrow's recommendation, tuned to today's signals, with a transparent
    explanation (Gloo-framed when credentials exist, deterministic otherwise)."""
    try:
        return circle.tomorrow(group_id=group_id, date_iso=date)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.get("/search", response_model=SearchResponse)
def search(
    q: str,
    top_k: int | None = None,
    translation: str | None = None,
    engine: RagEngine = Depends(get_engine),
) -> SearchResponse:
    if translation:
        engine.ensure_index(translation)
    results = engine.search(q, top_k)
    return SearchResponse(query=q, results=results)


# ---------------------------------------------------------------------------
# YouVersion Circle — standalone synthesis (for mock-mode live AI)
# ---------------------------------------------------------------------------

from pydantic import BaseModel as _BM


class SynthesizeRequest(_BM):
    tags: list[str] = []
    words: list[str] = []
    reflections: list[str] = []


@router.post("/circle/synthesize")
def synthesize(
    req: SynthesizeRequest,
    circle: CircleEngine = Depends(get_circle_engine),
) -> dict:
    """Standalone synthesis endpoint: accepts raw signals, returns AI summary.
    Used by mock-mode frontends to get live Gloo AI summaries."""
    llm = circle.engine.llm
    if llm is not None and getattr(llm, "configured", False):
        try:
            summary = circle._gloo_synthesis(req.tags, req.words, req.reflections)
            return {"summary": summary, "model": llm.name, "provider": "gloo"}
        except Exception:
            pass
    return {
        "summary": "Consider reaching out to someone in the group today with a word of encouragement.",
        "model": "circle-fallback",
        "provider": "fallback",
    }
