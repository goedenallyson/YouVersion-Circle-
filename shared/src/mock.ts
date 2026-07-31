// Mock API: a faithful in-browser reimplementation of the backend LumenEngine.
// Same public-domain WEB corpus, tag->theme map, deterministic (group,date)
// selection, curated emoji, named demo peers, adaptive synthesis, 1-3 verse
// passages, and structured recommendation plan. Lets the app run with no
// backend (offline demo / CI). Response shapes match the live API exactly.
import type {
  Config,
  EngagementSignal,
  GroupPulse,
  GroupSynthesis,
  LumenApi,
  Member,
  RecommendationPlan,
  SignalResponse,
  TomorrowRecommendation,
} from "./types";
import { seed } from "./seed";

interface Verse {
  book: string;
  chapter: number;
  verse: number;
  text: string;
  end_verse?: number | null;
  verse_count?: number;
}

const CORPUS: Verse[] = [
  { book: "John", chapter: 3, verse: 16, text: "For God so loved the world, that he gave his one and only Son, that whoever believes in him should not perish, but have eternal life." },
  { book: "John", chapter: 3, verse: 17, text: "For God didn't send his Son into the world to judge the world, but that the world should be saved through him." },
  { book: "Psalms", chapter: 23, verse: 1, text: "Yahweh is my shepherd; I shall lack nothing." },
  { book: "Psalms", chapter: 23, verse: 4, text: "Even though I walk through the valley of the shadow of death, I will fear no evil, for you are with me." },
  { book: "Proverbs", chapter: 3, verse: 5, text: "Trust in Yahweh with all your heart, and don't lean on your own understanding." },
  { book: "Proverbs", chapter: 3, verse: 6, text: "In all your ways acknowledge him, and he will make your paths straight." },
  { book: "Philippians", chapter: 4, verse: 6, text: "In nothing be anxious, but in everything, by prayer and petition with thanksgiving, let your requests be made known to God." },
  { book: "Philippians", chapter: 4, verse: 7, text: "And the peace of God, which surpasses all understanding, will guard your hearts and your thoughts in Christ Jesus." },
  { book: "Matthew", chapter: 6, verse: 33, text: "But seek first God's Kingdom and his righteousness; and all these things will be given to you as well." },
  { book: "Isaiah", chapter: 41, verse: 10, text: "Don't you be afraid, for I am with you. Don't be dismayed, for I am your God." },
  { book: "Romans", chapter: 8, verse: 28, text: "We know that all things work together for good for those who love God." },
  { book: "Jeremiah", chapter: 29, verse: 11, text: "For I know the thoughts that I think toward you, says Yahweh, thoughts of peace, and not of evil, to give you hope and a future." },
];

const TRANSLATION = "WEB";
const GROUP_NAME = "Tuesday Morning Circle";

export const APPROVED_EMOJI = ["🙌", "😊", "🎉", "🕊️", "😌", "🤲", "😢", "💔", "😟", "😔", "🌅", "💪", "✨", "🤔", "🙏", "❤️", "🤝", "🫂"];
const APPROVED_SET = new Set(APPROVED_EMOJI);

const MEMBERS: Member[] = [
  { id: "maya", name: "Maya", avatar: "🌿" },
  { id: "deacon", name: "Deacon", avatar: "🕊️" },
  { id: "ruth", name: "Ruth", avatar: "✨" },
  { id: "eli", name: "Eli", avatar: "🔥" },
  { id: "noor", name: "Noor", avatar: "🕊" },
];
const MEMBER_BY_ID: Record<string, Member> = Object.fromEntries(MEMBERS.map((m) => [m.id, m]));

const TAG_THEME: Record<string, string> = {
  Work: "calling and steadiness in work",
  Anxiety: "peace and rest from anxiety",
  Family: "patience and grace with family",
  Rest: "rest, renewal, and trust", 
  Hope: "hope and encouragement",
  Gratitude: "gratitude and joy",
};
const DEFAULT_THEMES = ["peace and rest from anxiety", "trust and guidance", "hope and encouragement", "rest, renewal, and trust", "strength and courage", "gratitude and joy", "God's love and presence"];
const THEME_HINTS: Record<string, string[]> = {
  "peace and rest from anxiety": ["peace", "anxious", "afraid", "rest"],
  "rest, renewal, and trust": ["trust", "rest", "shepherd", "lack"],
  "trust and guidance": ["trust", "paths", "acknowledge", "understanding"],
  "hope and encouragement": ["hope", "future", "good", "afraid"],
  "calling and steadiness in work": ["work", "good", "seek", "kingdom"],
  "patience and grace with family": ["love", "good", "peace", "grace"],
  "gratitude and joy": ["thanksgiving", "good", "gave", "joy"],
  "strength and courage": ["afraid", "dismayed", "with you", "strong"],
  "God's love and presence": ["loved", "with me", "gave", "God"],
};

const NEED_TAGS: Record<string, string> = {
  Work: "steadiness and calling in work",
  Anxiety: "peace in the middle of anxiety",
  Family: "patience and grace at home",
  Rest: "rest and permission to slow down",
};
const PRAISE_TAGS: Record<string, string> = {
  Hope: "renewed hope and encouragement",
  Gratitude: "gratitude and small joys",
};
const TAG_CLASSIFY: Record<string, [string, string]> = {
  Anxiety: ["top need", "Anxiety was the group\u2019s top need today"],
  Work: ["top need", "Steadiness in work was the group\u2019s top need today"],
  Family: ["top need", "Grace at home was the group\u2019s top need today"],
  Rest: ["top need", "Rest was the group\u2019s strongest shared need today"],
  Hope: ["shared theme", "Hope was the theme your group connected with most"],
  Gratitude: ["top praise", "Gratitude was the group\u2019s top praise today"],
};

export const SIGNAL_TAXONOMY: [string, string, string][] = [
  ["written reflection", "strong", "Strongest signal for needs, praises, and posture."],
  ["highlighted phrase", "strong", "Strong signal for what stood out in the passage."],
  ["cross-member themes", "strong", "Strong group-level signal when shared across members."],
  ["repeated needs/praises", "strong", "Useful long-term recommendation signal."],
  ["life-context tag", "moderate", "Supports theme detection; not decisive alone."],
  ["one-word reflection", "moderate", "Lightweight lexical signal."],
  ["selected emoji", "weak", "Lightweight emotional cue; never drives content alone."],
  ["engagement frequency", "context", "Confidence/cadence only, not content personalization."],
  ["passage themes", "context", "Context for interpreting engagement."],
  ["previous recommendations", "context", "Used to avoid repetition."],
];

const PEER_TAGS = ["Anxiety", "Rest", "Work", "Family", "Hope"];
const PEER_WORDS = ["peace", "still", "trust", "calm", "hope"];
const PEER_REACT = ["🙏", "❤️", "✨", "🕊️"];
const PEER_REFLECT = ["Needed this reminder to breathe today.", "Holding a friend in prayer this week.", "Grateful for a little unexpected rest.", "Work has been heavy but this steadied me."];

const iso = (d: Date) => d.toISOString().slice(0, 10);
const addDays = (dstr: string, n: number) => {
  const d = new Date(dstr + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return iso(d);
};
function citation(v: Verse) {
  return `${v.book} ${v.chapter}:${v.verse} (${TRANSLATION})`;
}
function citationRange(v: Verse) {
  return v.end_verse && v.end_verse !== v.verse
    ? `${v.book} ${v.chapter}:${v.verse}-${v.end_verse} (${TRANSLATION})`
    : citation(v);
}
function scoreVerse(v: Verse, theme: string) {
  const hints = THEME_HINTS[theme] || [];
  const t = v.text.toLowerCase();
  let s = 0;
  hints.forEach((h) => { if (t.includes(h)) s++; });
  return s;
}
function retrieve(theme: string): Verse[] {
  return [...CORPUS].map((v) => ({ v, s: scoreVerse(v, theme) })).sort((a, b) => b.s - a.s).slice(0, 5).map((x) => x.v);
}
function expandPassage(v: Verse): Verse {
  const same = CORPUS.filter((x) => x.book === v.book && x.chapter === v.chapter);
  const byV: Record<number, Verse> = {};
  same.forEach((x) => (byV[x.verse] = x));
  const verses = [v];
  let end = v.verse;
  while (verses.length < 3) {
    const nxt = byV[end + 1];
    if (!nxt) break;
    const words = verses.reduce((a, x) => a + x.text.split(/\s+/).length, 0) + nxt.text.split(/\s+/).length;
    const chars = verses.reduce((a, x) => a + x.text.length, 0) + nxt.text.length + 1;
    const needMore = verses[0].text.split(/\s+/).length < 12;
    if (!needMore && verses.length >= 1) break;
    if (words > 120 || chars > 690) break;
    verses.push(nxt);
    end = nxt.verse;
  }
  if (verses.length === 1) return { ...v, end_verse: null, verse_count: 1 };
  return { ...v, text: verses.map((x) => x.text).join(" "), end_verse: end, verse_count: verses.length };
}

function topOf<T>(arr: (T | null | undefined)[]): T | null {
  const c = new Map<T, number>();
  let best: T | null = null;
  let bn = 0;
  arr.forEach((x) => {
    if (x == null) return;
    const n = (c.get(x) || 0) + 1;
    c.set(x, n);
    if (n > bn) { bn = n; best = x; }
  });
  return best;
}
function topN(arr: string[], n: number): string[] {
  const c: Record<string, number> = {};
  arr.forEach((x) => { if (x) c[x] = (c[x] || 0) + 1; });
  return Object.entries(c).sort((a, b) => b[1] - a[1]).slice(0, n).map((x) => x[0]);
}
function joinList(a: string[]) {
  return a.length < 2 ? a[0] || "" : a.slice(0, -1).join(", ") + " and " + a[a.length - 1];
}
function classify(tag: string | null): [string, string] {
  if (tag && TAG_CLASSIFY[tag]) return TAG_CLASSIFY[tag];
  if (tag) return ["shared theme", `${tag} was the theme your group connected with most`];
  return ["common reflection", "Your circle is just getting started today"];
}
function confidence(tag: string | null, tags: string[], n: number) {
  if (!tag || n < 2) return "low";
  const share = tags.filter((t) => t === tag).length / (tags.length || 1);
  if (n >= 4 && share >= 0.5) return "high";
  if (n >= 3 && share >= 0.4) return "medium";
  return "low";
}
function engagementLevel(p: GroupPulse) {
  if (!p.unlocked || !p.total_responses) return "none";
  const s = p.total_responses + (p.reflection_count || 0) + (p.highlight_count || 0);
  return s >= 8 ? "high" : s >= 4 ? "medium" : "low";
}

function synthesize(all: EngagementSignal[]): GroupSynthesis {
  const tags = all.map((e) => e.tag).filter(Boolean) as string[];
  const words = all.map((e) => (e.word || "").toLowerCase()).filter(Boolean);
  const refs = all.map((e) => e.reflection).filter(Boolean) as string[];
  const needs = topN(tags.filter((t) => NEED_TAGS[t]), 3).map((t) => NEED_TAGS[t]);
  const praises = topN(tags.filter((t) => PRAISE_TAGS[t]), 3).map((t) => PRAISE_TAGS[t]);
  const themes = topN(tags, 3);
  const parts: string[] = [];
  if (needs.length) parts.push("the circle is carrying " + joinList(needs));
  if (praises.length) parts.push("and giving thanks for " + joinList(praises));
  if (words.length) parts.push("words that recurred: " + topN(words, 3).join(", "));
  const topTag = topOf(tags);
  const cl = classify(topTag);
  const conf = confidence(topTag, tags, all.length);
  let summary: string;
  if (!parts.length) {
    summary = "The circle is just getting started today — add a tag, word, or short reflection to shape the group's shared picture.";
  } else {
    summary = (cl[1] ? cl[1] + ". " : "") + "Today " + parts.join("; ") + ".";
    if (refs.length) summary += ` ${refs.length} member${refs.length !== 1 ? "s" : ""} shared a short reflection.`;
  }
  return { needs, praises, themes, summary, headline: cl[1], classification: cl[0], confidence: conf, response_count: all.length, model: "lumen-fallback", provider: "fallback" };
}

export function createMockApi(): LumenApi {
  const store: Record<string, EngagementSignal[]> = {};
  const dayEntries = (g: string, d: string) => store[`${g}|${d}`] || [];
  const streak = (g: string, d: string) => {
    let s = 0;
    let cur = d;
    while ((store[`${g}|${cur}`] || []).length > 0) { s++; cur = addDays(cur, -1); }
    return s;
  };
  async function themeFor(g: string, d: string) {
    const prev = dayEntries(g, addDays(d, -1));
    if (prev.length) {
      const tag = topOf(prev.map((e) => e.tag));
      if (tag && TAG_THEME[tag]) return TAG_THEME[tag];
    }
    const idx = seed(g, d) % DEFAULT_THEMES.length;
    return DEFAULT_THEMES[idx];
  }
  async function verseForTheme(theme: string, g: string, d: string) {
    const c = retrieve(theme);
    const idx = seed(g, d, theme) % c.length;
    return expandPassage(c[idx]);
  }
  async function demoPeers(g: string, d: string): Promise<EngagementSignal[]> {
    const base = seed(g, d);
    const pm = MEMBERS.slice(1, 4);
    return pm.map((m, i) => ({
      group_id: g,
      member_id: m.id,
      username: m.name,
      date: d,
      reaction: PEER_REACT[(base + i) % PEER_REACT.length],
      word: PEER_WORDS[(base + i) % PEER_WORDS.length],
      tag: PEER_TAGS[(base + i) % PEER_TAGS.length],
      reflection: i === 0 ? PEER_REFLECT[(base + i) % PEER_REFLECT.length] : null,
    }));
  }

  const api: LumenApi = {
    mode: "mock",
    async config(g) {
      return { group_id: g, group_name: GROUP_NAME, approved_emoji: APPROVED_EMOJI, privacy_notice: "Responses are shared with your group and are not anonymous. Group-level insights are AI-generated." } as Config;
    },
    async members(g) {
      return { group_id: g, members: MEMBERS };
    },
    async verseOfDay(g, d) {
      const theme = await themeFor(g, d);
      const v = await verseForTheme(theme, g, d);
      return { date: d, citation: citationRange(v), text: v.text, theme, translation: TRANSLATION, source: "local", verse_count: v.verse_count || 1, selection_source: "verse-of-day", selection_label: "Verse of the Day", group_streak: streak(g, d), unlocked: dayEntries(g, d).length > 0 };
    },
    async signal(sig: EngagementSignal): Promise<SignalResponse> {
      const d = sig.date as string;
      const key = `${sig.group_id}|${d}`;
      const arr = (store[key] = store[key] || []);
      if (sig.reaction && !APPROVED_SET.has(sig.reaction)) sig.reaction = null;
      if (!sig.username && sig.member_id && MEMBER_BY_ID[sig.member_id]) sig.username = MEMBER_BY_ID[sig.member_id].name;
      if (sig.member_id) {
        const i = arr.findIndex((e) => e.member_id === sig.member_id);
        if (i >= 0) arr[i] = sig; else arr.push(sig);
      } else arr.push(sig);
      return { accepted: true, verse: await api.verseOfDay(sig.group_id, d), pulse: await api.pulse(sig.group_id, d) };
    },
    async pulse(g, d): Promise<GroupPulse> {
      const real = dayEntries(g, d);
      const unlocked = real.length > 0;
      const responded = new Set(real.map((e) => e.member_id).filter(Boolean));
      const peers = unlocked ? (await demoPeers(g, d)).filter((p) => !responded.has(p.member_id)) : [];
      const all = unlocked ? real.concat(peers) : [];
      const tags = all.map((e) => e.tag).filter(Boolean) as string[];
      const words = all.map((e) => (e.word || "").toLowerCase()).filter(Boolean);
      const his = all.map((e) => e.highlight).filter(Boolean) as string[];
      const refs = all.map((e) => e.reflection).filter(Boolean);
      const reactions: Record<string, number> = {};
      all.forEach((e) => { if (e.reaction) reactions[e.reaction] = (reactions[e.reaction] || 0) + 1; });
      const topTag = topOf(tags);
      const topWord = topOf(words);
      const topHi = topOf(his);
      return {
        group_id: g, group_name: GROUP_NAME, date: d, unlocked, total_responses: all.length,
        top_tag: topTag,
        top_tag_pct: tags.length && topTag ? Math.round((100 * tags.filter((t) => t === topTag).length) / tags.length) : 0,
        top_word: topWord, top_highlight: topHi, highlight_count: topHi ? his.filter((h) => h === topHi).length : 0,
        reflection_count: refs.length, reactions, synthesis: unlocked ? synthesize(all) : null,
        entries: all.map((e) => ({ member_id: e.member_id || null, username: e.username || (e.member_id && MEMBER_BY_ID[e.member_id] ? MEMBER_BY_ID[e.member_id].name : e.member_id) || null, reaction: e.reaction || null, highlight: e.highlight || null, word: e.word || null, tag: e.tag || null, reflection: e.reflection || null })),
      };
    },
    async tomorrow(g, d): Promise<TomorrowRecommendation> {
      const tmr = addDays(d, 1);
      const p = await api.pulse(g, d);
      const theme = p.top_tag && TAG_THEME[p.top_tag] ? TAG_THEME[p.top_tag] : await themeFor(g, tmr);
      const todayCite = (await api.verseOfDay(g, d)).citation;
      const cands = retrieve(theme);
      const base = seed(g, tmr, theme) % (cands.length || 1);
      let v: Verse | null = null;
      const rejected: string[] = [];
      for (let off = 0; off < cands.length; off++) {
        const cand = expandPassage(cands[(base + off) % cands.length]);
        if (citationRange(cand) === todayCite && off < cands.length - 1) {
          rejected.push(citationRange(cand) + " (repeat of today)");
          continue;
        }
        v = cand;
        break;
      }
      if (!v) v = await verseForTheme(theme, g, tmr);
      const level = engagementLevel(p);
      const sig: string[] = [];
      if (p.top_tag) sig.push(`${p.top_tag_pct}% chose \u201c${p.top_tag}\u201d`);
      if (p.top_word) sig.push(`Top word: \u201c${p.top_word}\u201d`);
      if (p.top_highlight) sig.push(`\u201c${p.top_highlight}\u201d highlighted ${p.highlight_count}\u00d7`);
      if (p.reflection_count) sig.push(`${p.reflection_count} short reflection(s)`);
      if (level !== "none") sig.push(`engagement: ${level}`);
      sig.push(`theme shift: ${theme}`);
      let explanation: string;
      if (p.top_tag) {
        const depth = ({ high: "Your circle was very active today", medium: "Your circle engaged steadily today", low: "A couple of you responded today" } as Record<string, string>)[level] || "Your circle responded today";
        const reflect = p.reflection_count ? ` and ${p.reflection_count} shared a reflection` : "";
        explanation = `${depth}, leaning toward \u201c${p.top_tag}\u201d${p.top_word ? ` (top word: \u201c${p.top_word}\u201d)` : ""}${reflect}, so tomorrow shifts toward ${theme}.`;
      } else {
        explanation = `With no signals yet, tomorrow keeps a gentle rhythm around ${theme}. Add a reaction, highlight, or word to tune it to your group.`;
      }
      const reason = `theme=${theme}; engagement=${level}; top_tag=${p.top_tag}; reflections=${p.reflection_count}; based_on=${d}`;
      const syn = p.synthesis;
      const present: Record<string, boolean> = {
        "written reflection": p.reflection_count > 0,
        "highlighted phrase": !!p.top_highlight,
        "cross-member themes": !!(syn && syn.themes.length > 1),
        "repeated needs/praises": !!(syn && (syn.needs.length || syn.praises.length)),
        "life-context tag": !!p.top_tag,
        "one-word reflection": !!p.top_word,
        "selected emoji": !!Object.keys(p.reactions || {}).length,
        "engagement frequency": p.total_responses > 0,
        "passage themes": true,
        "previous recommendations": true,
      };
      const plan: RecommendationPlan = {
        workflow: ["Retrieve today's passage", "Collect member interactions", "Structure signals (highlights, emoji, words, reflections, tags)", "Classify themes/needs/praises (Gloo live, deterministic fallback)", "Aggregate at the group level with confidence weighting", "Identify strongest themes: " + theme, "Generate candidate passages", "Validate: context, translation, length (1-3 verses), safety, repetition", "Select: " + citationRange(v), "Store recommendation reason for debugging/eval"],
        signals: SIGNAL_TAXONOMY.map(([signal, strength, note]) => ({ signal, strength, present: !!present[signal], note })),
        strongest_themes: syn ? syn.themes : [theme],
        confidence: syn ? syn.confidence : "low",
        candidate_references: cands.map((c) => citationRange(c)),
        selected_reference: citationRange(v),
        rejected_candidates: rejected,
        safeguards_applied: ["Group-level weighting: no single member's response defines the pick.", "Repetition guard: today's passage is not recommended again.", "Scripture text comes only from YouVersion/local corpus, never AI-generated.", "AI summary is framed as insight, never quoted as Scripture.", "Negative emotion is not treated as a crisis."],
        reason,
      };
      return { date: tmr, based_on_date: d, theme, citation: citationRange(v), text: v.text, translation: TRANSLATION, source: "local", explanation, model: "lumen-fallback", signals: sig, engagement_level: level, verse_count: v.verse_count || 1, selection_source: "recommended-for-group", selection_label: "Recommended for Your Group", recommendation_reason: reason, rejected_candidates: rejected, plan };
    },
  };
  return api;
}

export const EMOTION_WORDS = ["peaceful", "grateful", "hopeful", "heavy", "restless", "joyful"];

export interface EngagementPair {
  pair: "emotion" | "reflection" | "word";
  placeholder?: string;
}

const ENGAGEMENT_PAIRS: EngagementPair[] = [
  { pair: "word" },
  { pair: "reflection", placeholder: "What do you hear God saying to you in this verse?" },
  { pair: "emotion" },
];

export function engagementPairForDay(_group: string, date: string): EngagementPair {
  const idx = seed(_group, date) % ENGAGEMENT_PAIRS.length;
  return ENGAGEMENT_PAIRS[idx];
}

export const todayIso = () => iso(new Date());
export const addDaysIso = addDays;
