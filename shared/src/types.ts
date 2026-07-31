// Shared response/request types — mirror the backend Pydantic schemas so the
// mock and live API implementations are interchangeable.

export interface Member {
  id: string;
  name: string;
  avatar?: string | null;
}

export interface Config {
  group_id: string;
  group_name: string;
  approved_emoji: string[];
  privacy_notice: string;
}

export interface VerseOfDay {
  date: string;
  citation: string;
  text: string;
  theme: string;
  translation: string;
  source: string;
  verse_count: number;
  selection_source: string;
  selection_label: string;
  group_streak: number;
  unlocked: boolean;
}

export interface EngagementSignal {
  group_id: string;
  member_id?: string | null;
  username?: string | null;
  date?: string | null;
  reaction?: string | null;
  highlight?: string | null;
  word?: string | null;
  tag?: string | null;
  reflection?: string | null;
}

export interface PulseEntry {
  member_id?: string | null;
  username?: string | null;
  reaction?: string | null;
  highlight?: string | null;
  word?: string | null;
  tag?: string | null;
  reflection?: string | null;
}

export interface GroupSynthesis {
  needs: string[];
  praises: string[];
  themes: string[];
  summary: string;
  headline: string;
  classification: string;
  confidence: string;
  response_count: number;
  model: string;
  provider: string;
}

export interface GroupPulse {
  group_id: string;
  group_name: string;
  date: string;
  unlocked: boolean;
  total_responses: number;
  top_tag?: string | null;
  top_tag_pct: number;
  top_word?: string | null;
  top_highlight?: string | null;
  highlight_count: number;
  reflection_count: number;
  reactions: Record<string, number>;
  synthesis?: GroupSynthesis | null;
  entries: PulseEntry[];
}

export interface SignalResponse {
  accepted: boolean;
  verse: VerseOfDay;
  pulse: GroupPulse;
}

export interface SignalStrength {
  signal: string;
  strength: string;
  present: boolean;
  note: string;
}

export interface RecommendationPlan {
  workflow: string[];
  signals: SignalStrength[];
  strongest_themes: string[];
  confidence: string;
  candidate_references: string[];
  selected_reference: string;
  rejected_candidates: string[];
  safeguards_applied: string[];
  reason: string;
}

export interface TomorrowRecommendation {
  date: string;
  based_on_date: string;
  theme: string;
  citation: string;
  text: string;
  translation: string;
  source: string;
  explanation: string;
  model: string;
  signals: string[];
  engagement_level: string;
  verse_count: number;
  selection_source: string;
  selection_label: string;
  recommendation_reason: string;
  rejected_candidates: string[];
  plan?: RecommendationPlan | null;
}

// The API surface both mock and live implementations satisfy.
export interface LumenApi {
  readonly mode: "mock" | "live";
  config(groupId: string): Promise<Config>;
  members(groupId: string): Promise<{ group_id: string; members: Member[] }>;
  verseOfDay(groupId: string, date: string): Promise<VerseOfDay>;
  signal(sig: EngagementSignal): Promise<SignalResponse>;
  pulse(groupId: string, date: string): Promise<GroupPulse>;
  tomorrow(groupId: string, date: string): Promise<TomorrowRecommendation>;
}
