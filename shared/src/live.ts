// Live API service: talks ONLY to our own backend (no API keys in the client).
// The backend proxies YouVersion/Gloo behind server-side credentials.
import type {
  Config,
  EngagementSignal,
  GroupPulse,
  CircleApi,
  Member,
  SignalResponse,
  TomorrowRecommendation,
  VerseOfDay,
} from "./types";

async function json<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as T;
}

export function createLiveApi(base: string): CircleApi {
  const b = base.replace(/\/$/, "");
  const q = (g: string, d?: string) =>
    `group_id=${encodeURIComponent(g)}${d ? `&date=${encodeURIComponent(d)}` : ""}`;
  return {
    mode: "live",
    config: (g) => fetch(`${b}/circle/config?${q(g)}`).then(json<Config>),
    members: (g) =>
      fetch(`${b}/circle/members?${q(g)}`).then(
        json<{ group_id: string; members: Member[] }>,
      ),
    verseOfDay: (g, d) =>
      fetch(`${b}/circle/verse-of-day?${q(g, d)}`).then(json<VerseOfDay>),
    signal: (sig: EngagementSignal) =>
      fetch(`${b}/circle/signal`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(sig),
      }).then(json<SignalResponse>),
    pulse: (g, d) => fetch(`${b}/circle/pulse?${q(g, d)}`).then(json<GroupPulse>),
    tomorrow: (g, d) =>
      fetch(`${b}/circle/tomorrow?${q(g, d)}`).then(json<TomorrowRecommendation>),
  };
}

/** Health-check a backend base URL; returns true if reachable + ok. */
export async function backendHealthy(base: string): Promise<boolean> {
  try {
    const r = await fetch(base.replace(/\/$/, "") + "/health");
    return r.ok;
  } catch {
    return false;
  }
}
