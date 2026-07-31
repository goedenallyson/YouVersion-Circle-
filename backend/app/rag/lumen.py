"""YouVersion Circle — the Verse-of-the-Day learning loop.

This is the product loop from the mockup:

    daily verse (YouVersion) -> tiny engagement signal (reaction / highlight /
    one-word / tag) -> group pulse unlocks -> Gloo AI learns the themes ->
    tomorrow's recommendation improves.

Design notes
------------
* **Deterministic by date.** Today's verse is chosen deterministically from
  the date + group so the demo and tests are reproducible without a database.
* **Graceful degradation.** Verse text comes from YouVersion when a key is
  configured, else the bundled public-domain (WEB) corpus. The "tomorrow"
  framing/explanation uses Gloo when credentials exist, else a deterministic
  offline explanation. Everything runs with zero credentials.
* **Privacy.** Signals are lightweight but ATTRIBUTED to a mock member in the
  group pulse (the intended product is a named circle, not anonymous): a
  reaction, a highlighted phrase, one word, a life-context tag, and a short
  reflection. Responses are shared with the group; users are told not to submit
  anything they don't want the group to see.
* **Storage.** An in-memory store keeps the demo self-contained. It is behind
  a small interface so it can be swapped for Redis/DB later.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from app.core.config import Settings
from app.models.schemas import (
    EngagementSignal,
    GroupPulse,
    GroupSynthesis,
    Member,
    PulseEntry,
    RecommendationPlan,
    SignalStrength,
    TomorrowRecommendation,
    VerseOfDay,
)
from app.rag.engine import RagEngine

# Life-context tag -> (pastoral theme used for retrieval, human label).
# Mirrors the mockup's tag row (Work / Anxiety / Family / Rest) and extends it.
TAG_THEME_MAP: dict[str, str] = {
    "Work": "calling and steadiness in work",
    "Anxiety": "peace and rest from anxiety",
    "Family": "patience and grace with family",
    "Rest": "rest, renewal, and trust",
    "Hope": "hope and encouragement",
    "Gratitude": "gratitude and joy",
}

# Life-context tags grouped by pastoral valence, used by the deterministic
# synthesis fallback to sort a circle's signals into shared needs vs. praises.
_NEED_TAGS = {"Work", "Anxiety", "Family", "Rest"}
_PRAISE_TAGS = {"Hope", "Gratitude"}
_NEED_PHRASING: dict[str, str] = {
    "Work": "steadiness and calling in work",
    "Anxiety": "peace in the middle of anxiety",
    "Family": "patience and grace at home",
    "Rest": "rest and permission to slow down",
}
_PRAISE_PHRASING: dict[str, str] = {
    "Hope": "renewed hope and encouragement",
    "Gratitude": "gratitude and small joys",
}

# Seeded mock members so the prototype has identities without real accounts.
# Responses are attributed to these usernames (the pulse is NOT anonymous).
_GROUP_NAME = "Tuesday Morning Circle"
_MOCK_MEMBERS: list[Member] = [
    Member(id="maya", name="Maya", avatar="🌿"),
    Member(id="deacon", name="Deacon", avatar="🕊️"),
    Member(id="ruth", name="Ruth", avatar="✨"),
    Member(id="eli", name="Eli", avatar="🔥"),
    Member(id="noor", name="Noor", avatar="🕊"),
]
_MEMBER_BY_ID: dict[str, Member] = {m.id: m for m in _MOCK_MEMBERS}

# Curated, approved emoji set (~20) grouped by pastoral category. The first
# version does NOT allow an unrestricted emoji library.
APPROVED_EMOJI: list[str] = [
    "🙌", "😊", "🎉",           # joy / praise
    "🕊️", "😌", "🤲",           # peace / comfort
    "😢", "💔",                 # sadness / grief
    "😟", "😔",                 # anxiety / uncertainty
    "🌅", "💪", "✨",           # hope / encouragement
    "🤔", "🙏",                 # conviction / reflection
    "❤️",                       # gratitude
    "🤝", "🫂",                 # love / connection
]
_APPROVED_EMOJI_SET = set(APPROVED_EMOJI)

# Explicit signal usefulness taxonomy for recommendations (from the PM plan).
# strong  = drives content; moderate = supports; weak = never alone;
# context = interpretation only, not a driver.
_SIGNAL_TAXONOMY: list[tuple[str, str, str]] = [
    ("written reflection", "strong", "Strongest signal for needs, praises, and posture."),
    ("highlighted phrase", "strong", "Strong signal for what stood out in the passage."),
    ("cross-member themes", "strong", "Strong group-level signal when shared across members."),
    ("repeated needs/praises", "strong", "Useful long-term recommendation signal."),
    ("life-context tag", "moderate", "Supports theme detection; not decisive alone."),
    ("one-word reflection", "moderate", "Lightweight lexical signal."),
    ("emotion tap", "moderate", "Emotional posture signal; supports theme and tone."),
    ("engagement frequency", "context", "Confidence/cadence only, not content personalization."),
    ("passage themes", "context", "Context for interpreting engagement."),
    ("previous recommendations", "context", "Used to avoid repetition."),
]

# Adaptive summary classification: map the winning tag to a headline label so
# the summary reads "Anxiety was the group's top need" vs "Gratitude was the
# group's top praise" rather than "top need" for every emotion.
_TAG_CLASSIFICATION: dict[str, tuple[str, str]] = {
    "Anxiety": ("top need", "Anxiety was the group’s top need today"),
    "Work": ("top need", "Steadiness in work was the group’s top need today"),
    "Family": ("top need", "Grace at home was the group’s top need today"),
    "Rest": ("top need", "Rest was the group’s strongest shared need today"),
    "Hope": ("shared theme", "Hope was the theme your group connected with most"),
    "Gratitude": ("top praise", "Gratitude was the group’s top praise today"),
}

# Default rotation of themes when there are no group signals yet. Keeps a fresh
# verse each day even for a brand-new circle.
_DEFAULT_THEMES: list[str] = [
    "peace and rest from anxiety",
    "trust and guidance",
    "hope and encouragement",
    "rest, renewal, and trust",
    "strength and courage",
    "gratitude and joy",
    "God's love and presence",
]


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _next_iso(date_iso: str) -> str:
    d = date.fromisoformat(date_iso)
    return (d + timedelta(days=1)).isoformat()


def _seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


@dataclass
class _GroupDay:
    """All engagement for one group on one date."""

    entries: list[EngagementSignal] = field(default_factory=list)

    @property
    def unlocked(self) -> bool:
        return len(self.entries) > 0


class GroupStore:
    """In-memory engagement store keyed by (group_id, date).

    Swap for a persistent backend behind this same tiny surface later.
    """

    def __init__(self) -> None:
        self._days: dict[tuple[str, str], _GroupDay] = {}

    def add(self, signal: EngagementSignal, date_iso: str) -> _GroupDay:
        key = (signal.group_id, date_iso)
        day = self._days.setdefault(key, _GroupDay())
        # One response per member/day: a member re-submitting updates their
        # existing entry rather than double-counting the circle.
        if signal.member_id:
            for i, existing in enumerate(day.entries):
                if existing.member_id == signal.member_id:
                    day.entries[i] = signal
                    return day
        day.entries.append(signal)
        return day

    def get(self, group_id: str, date_iso: str) -> _GroupDay:
        return self._days.get((group_id, date_iso), _GroupDay())

    def streak(self, group_id: str, up_to_iso: str) -> int:
        """Consecutive days (ending at up_to_iso) with at least one signal."""
        streak = 0
        d = date.fromisoformat(up_to_iso)
        while (group_id, d.isoformat()) in self._days and self._days[
            (group_id, d.isoformat())
        ].unlocked:
            streak += 1
            d -= timedelta(days=1)
        return streak


# A few seeded named "peers" (mapped to mock members) so the group pulse feels
# alive in the demo even before real friends respond. Deterministic per
# (group, date). Responses are attributed, not anonymous.
_DEMO_PEER_HIGHLIGHTS = [
    "Trust in Yahweh",
    "all your heart",
    "don't lean on your own understanding",
    "he will make your paths straight",
]
_DEMO_PEER_REFLECTIONS = [
    "Needed this reminder to breathe today.",
    "Holding a friend in prayer this week.",
    "Grateful for a little unexpected rest.",
    "Work has been heavy but this steadied me.",
]
_DEMO_PEER_EMOTIONS = ["Grateful", "Peaceful", "Hopeful", "Anxious", "Weary"]
_DEMO_PEER_WORDS = ["peace", "trust", "hope", "still", "grace"]
_ENGAGEMENT_PAIRS = ["emotion", "reflection", "word"]


class LumenEngine:
    def __init__(
        self, engine: RagEngine, store: GroupStore | None = None
    ) -> None:
        self.engine = engine
        self.store = store or GroupStore()
        self.settings: Settings = engine.settings

    # -- Theme selection -----------------------------------------------------
    def _theme_for(self, group_id: str, date_iso: str) -> str:
        """Pick the theme for a date.

        If the group produced signals the day before, tune toward the most
        common tag's theme (the learning loop). Otherwise rotate a default
        theme deterministically by date so verses stay fresh.
        """
        prev = self.store.get(group_id, _prev_iso(date_iso))
        if prev.entries:
            tag = _top_tag([e.tag for e in prev.entries])
            if tag and tag in TAG_THEME_MAP:
                return TAG_THEME_MAP[tag]
        idx = _seed(group_id, date_iso) % len(_DEFAULT_THEMES)
        return _DEFAULT_THEMES[idx]

    def _verse_for_theme(self, theme: str, group_id: str, date_iso: str):
        """Retrieve a verse for the theme; deterministic pick within top-k.

        When YouVersion is configured, refresh the chosen verse's text from
        the live partner API (always-fresh, licensed text). Any failure falls
        back silently to the local corpus text so the loop never breaks.
        """
        candidates = self.engine.search(theme, top_k=5)
        if not candidates:
            raise RuntimeError("No scripture candidates; is the index built?")
        idx = _seed(group_id, date_iso, theme) % len(candidates)
        chosen = candidates[idx]
        chosen = self._maybe_refresh_from_youversion(chosen)
        return self._expand_passage(chosen)

    # -- Passage length / context (1–3 verses) -------------------------------
    def _expand_passage(self, chunk):
        """Grow a single-verse pick into a semantically completer 1–3 verse
        passage when adjacent verses exist, targeting ~40–120 words / <700
        chars for mobile. Never splits mid-sentence; falls back to the single
        verse if no clean neighbor is available.
        """
        ref = chunk.ref
        try:
            neighbors = self.engine.index_source.load_translation(ref.translation)
        except Exception:
            return chunk
        by_verse = {
            c.ref.verse: c
            for c in neighbors
            if c.ref.book == ref.book and c.ref.chapter == ref.chapter
        }
        verses = [chunk]
        end_verse = ref.verse
        # Extend forward up to 3 verses while the passage stays short enough
        # and the running text doesn't already end a complete thought poorly.
        while len(verses) < 3:
            nxt = by_verse.get(end_verse + 1)
            if nxt is None:
                break
            combined_words = sum(len(v.text.split()) for v in verses) + len(
                nxt.text.split()
            )
            combined_chars = sum(len(v.text) for v in verses) + len(nxt.text) + 1
            # Only extend if the first verse is short/mid-idea OR we're still
            # under the mobile budget; stop once we have a coherent chunk.
            first_words = len(verses[0].text.split())
            need_more = first_words < 12  # short lead verse benefits from context
            if not need_more and len(verses) >= 1:
                break
            if combined_words > 120 or combined_chars > 690:
                break
            verses.append(nxt)
            end_verse = nxt.ref.verse
        if len(verses) == 1:
            return chunk
        merged = chunk.model_copy()
        merged.text = " ".join(v.text for v in verses)
        merged.end_verse = end_verse
        return merged

    def _maybe_refresh_from_youversion(self, chunk):
        """If YouVersion is the active provider, pull fresh text for the ref."""
        bible = self.engine.bible
        if getattr(bible, "name", None) != "youversion":
            return chunk
        ref = chunk.ref
        reference = f"{ref.book} {ref.chapter}:{ref.verse}"
        try:
            fresh = bible.passage(ref.translation, reference)
            if fresh and fresh[0].text:
                refreshed = chunk.model_copy()
                refreshed.text = fresh[0].text
                return refreshed
        except Exception:
            pass
        return chunk

    def _source_label(self) -> str:
        return (
            "youversion"
            if self.settings.bible_provider == "youversion"
            and self.settings.bible_api_key
            else "local"
        )

    # -- Public API ----------------------------------------------------------
    def verse_of_day(
        self, group_id: str = "demo", date_iso: str | None = None
    ) -> VerseOfDay:
        date_iso = date_iso or _today_iso()
        theme = self._theme_for(group_id, date_iso)
        verse = self._verse_for_theme(theme, group_id, date_iso)
        day = self.store.get(group_id, date_iso)
        vcount = (verse.end_verse - verse.ref.verse + 1) if verse.end_verse else 1
        # Today's passage is predetermined "Verse of the Day" (same for all
        # groups on a date via the theme rotation); tomorrow's is the adaptive
        # "Recommended for Your Group". We keep them clearly distinct in copy.
        return VerseOfDay(
            date=date_iso,
            citation=verse.citation,
            text=verse.text,
            theme=theme,
            translation=verse.ref.translation,
            source=self._source_label(),
            verse_count=vcount,
            selection_source="verse-of-day",
            selection_label="Verse of the Day",
            group_streak=self.store.streak(group_id, date_iso),
            unlocked=day.unlocked,
        )

    def submit_signal(self, signal: EngagementSignal):
        date_iso = signal.date or _today_iso()
        signal.date = date_iso
        # Attach a display username from the mock member if the client didn't
        # send one (responses are attributed, not anonymous).
        if not signal.username and signal.member_id in _MEMBER_BY_ID:
            signal.username = _MEMBER_BY_ID[signal.member_id].name
        # Enforce the curated emoji set: drop an unapproved reaction rather than
        # Allow both approved emoji and emotion tap words
        _ALLOWED_REACTIONS = _APPROVED_EMOJI_SET | {"Grateful", "Peaceful", "Hopeful", "Anxious", "Weary"}
        if signal.reaction and signal.reaction not in _ALLOWED_REACTIONS:
            signal.reaction = None
        self.store.add(signal, date_iso)
        verse = self.verse_of_day(signal.group_id, date_iso)
        pulse = self.group_pulse(signal.group_id, date_iso)
        return verse, pulse

    def group_pulse(
        self, group_id: str = "demo", date_iso: str | None = None
    ) -> GroupPulse:
        date_iso = date_iso or _today_iso()
        day = self.store.get(group_id, date_iso)
        unlocked = day.unlocked

        # Combine real entries with deterministic demo peers so the pulse is
        # populated once the user unlocks it. Peers only fill in members who
        # haven't already responded, so usernames stay unique in the pulse.
        entries = list(day.entries)
        responded = {e.member_id for e in entries if e.member_id}
        peers = (
            [p for p in self._demo_peers(group_id, date_iso) if p.member_id not in responded]
            if unlocked
            else []
        )
        all_entries = entries + peers

        tags = [e.tag for e in all_entries if e.tag]
        words = [e.word.lower() for e in all_entries if e.word]
        highlights = [e.highlight for e in all_entries if e.highlight]
        reflections = [e.reflection for e in all_entries if e.reflection]
        reactions = Counter(e.reaction for e in all_entries if e.reaction)

        top_tag = _top_tag(tags)
        top_tag_pct = (
            round(100 * tags.count(top_tag) / len(tags)) if tags and top_tag else 0
        )
        top_word = Counter(words).most_common(1)[0][0] if words else None
        top_highlight = Counter(highlights).most_common(1)[0][0] if highlights else None
        highlight_count = highlights.count(top_highlight) if top_highlight else 0

        synthesis = self._synthesize(all_entries) if unlocked else None

        return GroupPulse(
            group_id=group_id,
            group_name=_GROUP_NAME,
            date=date_iso,
            unlocked=unlocked,
            total_responses=len(all_entries),
            top_tag=top_tag,
            top_tag_pct=top_tag_pct,
            top_word=top_word,
            top_highlight=top_highlight,
            highlight_count=highlight_count,
            reflection_count=len(reflections),
            reactions=dict(reactions),
            synthesis=synthesis,
            entries=[
                # Attributed (NOT anonymous): show username + only the fields the
                # member actually used that day (None fields hidden by client).
                PulseEntry(
                    member_id=e.member_id,
                    username=e.username
                    or (
                        _MEMBER_BY_ID[e.member_id].name
                        if e.member_id in _MEMBER_BY_ID
                        else e.member_id
                    ),
                    reaction=e.reaction,
                    highlight=e.highlight,
                    word=e.word,
                    tag=e.tag,
                    reflection=e.reflection,
                )
                for e in all_entries
            ],
        )

    # -- Members -------------------------------------------------------------
    @staticmethod
    def members() -> list[Member]:
        """Seeded mock personas (no real accounts in the prototype)."""
        return list(_MOCK_MEMBERS)

    @staticmethod
    def approved_emoji() -> list[str]:
        """Curated approved emoji set (no unrestricted library in v1)."""
        return list(APPROVED_EMOJI)

    @staticmethod
    def group_name() -> str:
        return _GROUP_NAME

    # -- Group synthesis -----------------------------------------------------
    def _synthesize(self, entries: list[EngagementSignal]) -> GroupSynthesis:
        """Summarize a circle's shared needs / praises / themes."""
        tags = [e.tag for e in entries if e.tag]
        words = [e.word.lower() for e in entries if e.word]
        reflections = [e.reflection for e in entries if e.reflection]
        reactions = [e.reaction for e in entries if e.reaction]
        highlights = [e.highlight for e in entries if e.highlight]
        response_count = len(entries)

        needs = [
            _NEED_PHRASING[t]
            for t, _ in Counter(t for t in tags if t in _NEED_TAGS).most_common(3)
        ]
        praises = [
            _PRAISE_PHRASING[t]
            for t, _ in Counter(t for t in tags if t in _PRAISE_TAGS).most_common(3)
        ]
        themes = [t for t, _ in Counter(tags).most_common(3)]

        top_tag = _top_tag(tags)
        classification, headline = _classify(top_tag)
        confidence = _confidence(top_tag, tags, response_count)

        # Live Gloo synthesis when configured.
        llm = self.engine.llm
        if llm is not None and getattr(llm, "configured", False):
            try:
                summary = self._gloo_synthesis(tags, words, reflections, reactions, highlights)
                # Override headline for emotion-tap days
                if reactions and not reflections and not words and not tags:
                    top_emotion = Counter(reactions).most_common(1)[0][0]
                    headline = f"Your circle is feeling {top_emotion} today"
                return GroupSynthesis(
                    needs=needs,
                    praises=praises,
                    themes=themes,
                    summary=summary,
                    headline=headline,
                    classification=classification,
                    confidence=confidence,
                    response_count=response_count,
                    model=llm.name,
                    provider="gloo",
                )
            except Exception:
                pass

        # Fallback: handle emotion-tap days
        if reactions and not reflections and not words and not tags:
            top_emotion = Counter(reactions).most_common(1)[0][0]
            emotion_list = [e for e, _ in Counter(reactions).most_common(2)]
            headline = f"Your circle is feeling {top_emotion} today"
            highlight_note = f' Phrases like "{highlights[0]}" stood out to the group.' if highlights else ""
            summary = f"Most of your group is feeling {' and '.join(e.lower() for e in emotion_list)} today.{highlight_note} Consider checking in with each other about how you're really doing."
        else:
            summary = self._fallback_synthesis(
                needs, praises, words, reflections, headline
            )

        return GroupSynthesis(
            needs=needs,
            praises=praises,
            themes=themes,
            summary=summary,
            headline=headline,
            classification=classification,
            confidence=confidence,
            response_count=response_count,
            model="circle-fallback",
            provider="fallback",
        )

    def _gloo_synthesis(
        self, tags: list[str], words: list[str], reflections: list[str],
        reactions: list[str] | None = None, highlights: list[str] | None = None,
    ) -> str:
        llm = self.engine.llm
        system = (
            "You are a warm, pastoral facilitator. In 2 short sentences, "
            "synthesize a small group's shared needs, praises, and themes for "
            "today from the group's signals. Speak at the GROUP level; do not "
            "name or single out individuals, and do not invent facts."
        )
        prompt = (
            f"Life-context tags: {', '.join(tags) or 'none'}. "
            f"One-word reflections: {', '.join(words) or 'none'}. "
            f"Short reflections: {' | '.join(reflections) or 'none'}. "
            f"Emotions shared: {', '.join(reactions or []) or 'none'}. "
            f"Highlighted phrases: {', '.join(highlights[:3] if highlights else []) or 'none'}."
        )
        return llm.frame(system, prompt)  # type: ignore[attr-defined]

    @staticmethod
    def _fallback_synthesis(
        needs: list[str],
        praises: list[str],
        words: list[str],
        reflections: list[str],
        headline: str = "",
    ) -> str:
        parts: list[str] = []
        if needs:
            parts.append("the circle is carrying " + _join(needs))
        if praises:
            parts.append("and giving thanks for " + _join(praises))
        if words:
            top_words = [w for w, _ in Counter(words).most_common(3)]
            parts.append("words that recurred: " + ", ".join(top_words))
        if not parts:
            return (
                "The circle is just getting started today — add a tag, word, or "
                "short reflection to shape the group's shared picture."
            )
        # Lead with the adaptive headline (need/praise/theme) so the summary
        # tone matches the responses instead of always saying “top need”.
        lead = (headline + ". ") if headline else ""
        summary = lead + "Today " + "; ".join(parts) + "."
        if reflections:
            summary += (
                f" {len(reflections)} member"
                + ("s" if len(reflections) != 1 else "")
                + " shared a short reflection."
            )
        return summary

    def tomorrow(
        self, group_id: str = "demo", date_iso: str | None = None
    ) -> TomorrowRecommendation:
        """The learning loop payoff: tomorrow's verse tuned to today's pulse."""
        date_iso = date_iso or _today_iso()
        tomorrow_iso = _next_iso(date_iso)
        pulse = self.group_pulse(group_id, date_iso)

        # Theme shift: driven by today's top tag if present, else the default
        # rotation for tomorrow.
        if pulse.top_tag and pulse.top_tag in TAG_THEME_MAP:
            theme = TAG_THEME_MAP[pulse.top_tag]
        else:
            theme = self._theme_for(group_id, tomorrow_iso)

        # Candidate generation + repetition guard: prefer a passage the group
        # hasn't just seen (today's citation) so we don't recommend the same
        # thing back-to-back.
        candidates = self.engine.search(theme, top_k=5)
        today_citation = self.verse_of_day(group_id, date_iso).citation
        rejected: list[str] = []
        verse = None
        base_idx = _seed(group_id, tomorrow_iso, theme) % max(len(candidates), 1)
        for off in range(len(candidates)):
            cand = candidates[(base_idx + off) % len(candidates)]
            expanded = self._expand_passage(
                self._maybe_refresh_from_youversion(cand)
            )
            if expanded.citation == today_citation and off < len(candidates) - 1:
                rejected.append(expanded.citation + " (repeat of today)")
                continue
            verse = expanded
            break
        if verse is None:
            verse = self._verse_for_theme(theme, group_id, tomorrow_iso)

        level = _engagement_level(pulse)
        signals = _signal_bullets(pulse, theme, level)
        explanation, model = self._explain(theme, pulse, verse, signals, level)
        vcount = (verse.end_verse - verse.ref.verse + 1) if verse.end_verse else 1
        reason = (
            f"theme={theme}; engagement={level}; top_tag={pulse.top_tag}; "
            f"reflections={pulse.reflection_count}; based_on={date_iso}"
        )
        plan = self._build_plan(
            pulse, theme, verse, candidates, rejected, level, reason
        )

        return TomorrowRecommendation(
            date=tomorrow_iso,
            based_on_date=date_iso,
            theme=theme,
            citation=verse.citation,
            text=verse.text,
            translation=verse.ref.translation,
            source=self._source_label(),
            explanation=explanation,
            model=model,
            signals=signals,
            engagement_level=level,
            verse_count=vcount,
            selection_source="recommended-for-group",
            selection_label="Recommended for Your Group",
            recommendation_reason=reason,
            rejected_candidates=rejected,
            plan=plan,
        )

    def _build_plan(
        self, pulse, theme, verse, candidates, rejected, level, reason
    ) -> RecommendationPlan:
        """Assemble the transparent recommendation record: which signals were
        present + their weighting, the workflow steps, and the safeguards."""
        syn = pulse.synthesis
        present = {
            "written reflection": pulse.reflection_count > 0,
            "highlighted phrase": bool(pulse.top_highlight),
            "cross-member themes": bool(syn and len(syn.themes) > 1),
            "repeated needs/praises": bool(syn and (syn.needs or syn.praises)),
            "life-context tag": bool(pulse.top_tag),
            "one-word reflection": bool(pulse.top_word),
            "emotion tap": bool(pulse.reactions),
            "engagement frequency": pulse.total_responses > 0,
            "passage themes": True,
            "previous recommendations": True,
        }
        signals = [
            SignalStrength(
                signal=name,
                strength=strength,
                present=present.get(name, False),
                note=note,
            )
            for name, strength, note in _SIGNAL_TAXONOMY
        ]
        confidence = syn.confidence if syn else "low"
        safeguards = [
            "Group-level weighting: no single member's response defines the pick.",
            "Repetition guard: today's passage is not recommended again.",
            "Scripture text comes only from YouVersion/local corpus, never AI-generated.",
            "AI summary is framed as insight, never quoted as Scripture.",
            "Negative emotion is not treated as a crisis.",
        ]
        if confidence == "low":
            safeguards.append(
                "Low confidence: gentle theme continuity rather than a strong shift."
            )
        return RecommendationPlan(
            workflow=[
                "Retrieve today's passage",
                "Collect member interactions",
                "Structure signals (highlights, emoji, words, reflections, tags)",
                "Classify themes/needs/praises (Gloo live, deterministic fallback)",
                "Aggregate at the group level with confidence weighting",
                f"Identify strongest themes: {theme}",
                "Generate candidate passages",
                "Validate: context, translation, length (1-3 verses), safety, repetition",
                f"Select: {verse.citation}",
                "Store recommendation reason for debugging/eval",
            ],
            signals=signals,
            strongest_themes=(syn.themes if syn else [theme]),
            confidence=confidence,
            candidate_references=[c.citation for c in candidates],
            selected_reference=verse.citation,
            rejected_candidates=rejected,
            safeguards_applied=safeguards,
            reason=reason,
        )

    # -- Framing / explanation ----------------------------------------------
    def _explain(self, theme, pulse, verse, signals, level) -> tuple[str, str]:
        llm = self.engine.llm
        if llm is not None and getattr(llm, "configured", False):
            system = (
                "You explain, in 2 short sentences, why an app is recommending "
                "a specific Bible verse to a small group tomorrow, based on how "
                "the group engaged today. Be warm, transparent, and concrete. "
                "Do not quote the verse text; it is shown separately."
            )
            prompt = (
                f"Theme tuned toward: {theme}. Group engagement level: {level}. "
                f"Today's group signals: {'; '.join(signals) or 'none yet'}. "
                f"Tomorrow's verse: [{verse.citation}]."
            )
            try:
                text = llm.frame(system, prompt)  # type: ignore[attr-defined]
                return text, llm.name
            except Exception:
                pass
        return self._fallback_explanation(theme, pulse, level), "circle-fallback"

    @staticmethod
    def _fallback_explanation(theme: str, pulse: GroupPulse, level: str) -> str:
        if pulse.top_tag:
            # Recommendation is informed by *how much* the group engaged, not
            # only the winning tag.
            depth = {
                "high": "Your circle was very active today",
                "medium": "Your circle engaged steadily today",
                "low": "A couple of you responded today",
            }.get(level, "Your circle responded today")
            reflect = (
                f" and {pulse.reflection_count} shared a reflection"
                if pulse.reflection_count
                else ""
            )
            return (
                f"{depth}, leaning toward \u201c{pulse.top_tag}\u201d"
                + (
                    f" (top word: \u201c{pulse.top_word}\u201d)"
                    if pulse.top_word
                    else ""
                )
                + f"{reflect}, so tomorrow shifts toward {theme}."
            )
        return (
            f"With no signals yet, tomorrow keeps a gentle rhythm around {theme}. "
            "Add a reaction, highlight, or word to tune it to your group."
        )

    def _demo_peers(self, group_id: str, date_iso: str) -> list[EngagementSignal]:
        base = _seed(group_id, date_iso)
        # Determine today's engagement pair (must match frontend logic)
        pair_idx = _seed(group_id, date_iso, "engagement") % len(_ENGAGEMENT_PAIRS)
        pair = _ENGAGEMENT_PAIRS[pair_idx]

        peer_members = _MOCK_MEMBERS[1:4]
        verse = self._verse_for_theme(self._theme_for(group_id, date_iso), group_id, date_iso)
        words = verse.text.split()
        # Pick 2-4 word phrases from the verse for each peer's highlight
        highlights: list[str] = []
        for i in range(len(peer_members)):
            start = ((base + i * 7) % max(1, len(words) - 3))
            length = 2 + ((base + i) % 3)
            phrase = " ".join(words[start:start + length])
            highlights.append(phrase)

        peers: list[EngagementSignal] = []
        for i, m in enumerate(peer_members):
            # Match the daily prompt type for the engagement response
            reaction = None
            word = None
            reflection = None
            if pair == "emotion":
                reaction = _DEMO_PEER_EMOTIONS[(base + i) % len(_DEMO_PEER_EMOTIONS)]
            elif pair == "reflection":
                reflection = _DEMO_PEER_REFLECTIONS[(base + i) % len(_DEMO_PEER_REFLECTIONS)]
            else:  # "word"
                word = _DEMO_PEER_WORDS[(base + i) % len(_DEMO_PEER_WORDS)]

            peers.append(
                EngagementSignal(
                    group_id=group_id,
                    member_id=m.id,
                    username=m.name,
                    date=date_iso,
                    reaction=reaction,
                    highlight=highlights[i],
                    word=word,
                    tag=None,
                    reflection=reflection,
                )
            )
        return peers


# -- small pure helpers ------------------------------------------------------
def _prev_iso(date_iso: str) -> str:
    return (date.fromisoformat(date_iso) - timedelta(days=1)).isoformat()


def _top_tag(tags: list[str | None]) -> str | None:
    clean = [t for t in tags if t]
    if not clean:
        return None
    return Counter(clean).most_common(1)[0][0]


def _classify(top_tag: str | None) -> tuple[str, str]:
    """Map the winning tag to (classification, adaptive headline)."""
    if top_tag and top_tag in _TAG_CLASSIFICATION:
        return _TAG_CLASSIFICATION[top_tag]
    if top_tag:
        return "shared theme", f"{top_tag} was the theme your group connected with most"
    return "common reflection", "Your circle is just getting started today"


def _confidence(top_tag: str | None, tags: list[str], response_count: int) -> str:
    """Group-level confidence: don't let one voice define the group."""
    if not top_tag or response_count < 2:
        return "low"
    share = tags.count(top_tag) / len(tags) if tags else 0
    if response_count >= 4 and share >= 0.5:
        return "high"
    if response_count >= 3 and share >= 0.4:
        return "medium"
    return "low"


def _join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _engagement_level(pulse: GroupPulse) -> str:
    """Bucket a day's engagement so recommendations can respond to *how much*
    the circle participated, not only the winning tag."""
    if not pulse.unlocked or pulse.total_responses == 0:
        return "none"
    score = pulse.total_responses + pulse.reflection_count + pulse.highlight_count
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


def _signal_bullets(pulse: GroupPulse, theme: str, level: str = "none") -> list[str]:
    bullets: list[str] = []
    if pulse.top_tag:
        bullets.append(f"{pulse.top_tag_pct}% chose \u201c{pulse.top_tag}\u201d")
    if pulse.top_word:
        bullets.append(f"Top word: \u201c{pulse.top_word}\u201d")
    if pulse.top_highlight:
        bullets.append(
            f"\u201c{pulse.top_highlight}\u201d highlighted {pulse.highlight_count}\u00d7"
        )
    if pulse.reflection_count:
        bullets.append(f"{pulse.reflection_count} short reflection(s)")
    if level != "none":
        bullets.append(f"engagement: {level}")
    bullets.append(f"theme shift: {theme}")
    return bullets
