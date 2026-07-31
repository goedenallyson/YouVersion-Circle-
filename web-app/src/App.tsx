import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createMockApi, todayIso, addDaysIso, engagementPairForDay, EMOTION_WORDS } from "./api/mock";
import { createLiveApi, backendHealthy } from "./api/live";
import type {
  Config,
  GroupPulse,
  LumenApi,
  Member,
  TomorrowRecommendation,
  VerseOfDay,
} from "./api/types";
import { PassageHighlighter } from "./components/PassageHighlighter";
import { GroupPulseView } from "./components/GroupPulseView";
import { RecommendationPlanView } from "./components/RecommendationPlanView";

const GROUP = "demo";
const API_BASE = (import.meta.env.VITE_API_BASE as string) || "/api/v1";

export function App() {
  const [api, setApi] = useState<LumenApi>(() => createMockApi());
  const [step, setStep] = useState(0);
  const [date, setDate] = useState(todayIso());
  const memberId = "maya";
  const [members, setMembers] = useState<Member[]>([]);
  const [config, setConfig] = useState<Config | null>(null);
  const [verse, setVerse] = useState<VerseOfDay | null>(null);
  const [pulse, setPulse] = useState<GroupPulse | null>(null);
  const [tomorrow, setTomorrow] = useState<TomorrowRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  // engagement state
  const [reaction, setReaction] = useState<string | null>(null);
  const [tag, setTag] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [word, setWord] = useState("");
  const [reflection, setReflection] = useState("");

  const [toast, setToast] = useState("");
  const toastTimer = useRef<number>();
  const showToast = useCallback((m: string) => {
    setToast(m);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(""), 1500);
  }, []);

  const membersById = useMemo(
    () => Object.fromEntries(members.map((m) => [m.id, m])) as Record<string, Member>,
    [members],
  );

  const bootstrap = useCallback(
    async (a: LumenApi) => {
      try {
        const [cfg, mem] = await Promise.all([a.config(GROUP), a.members(GROUP)]);
        setConfig(cfg);
        setMembers(mem.members);
      } catch {
        /* keep defaults */
      }
    },
    [],
  );

  const loadVerse = useCallback(
    async (a: LumenApi, d: string) => {
      try {
        setVerse(await a.verseOfDay(GROUP, d));
        setError(null);
      } catch (e) {
        setError("Could not load today's passage: " + (e as Error).message);
      }
    },
    [],
  );

  useEffect(() => {
    (async () => {
      let chosen: LumenApi;
      if (await backendHealthy(API_BASE)) {
        chosen = createLiveApi(API_BASE);
      } else {
        chosen = createMockApi();
      }
      setApi(chosen);
      await bootstrap(chosen);
      await loadVerse(chosen, date);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetEngagement = () => {
    setReaction(null);
    setTag(null);
    setHighlight(null);
    setWord("");
    setReflection("");
  };

  const submit = async () => {
    if (!highlight) {
      showToast("Highlight a word or phrase first");
      return;
    }
    if (!reaction && !word.trim() && !reflection.trim()) {
      showToast("Complete the engagement pair to unlock");
      return;
    }
    try {
      const res = await api.signal({
        group_id: GROUP,
        member_id: memberId,
        date,
        reaction,
        highlight,
        word: word.trim() || null,
        tag,
        reflection: reflection.trim() || null,
      });
      setPulse(res.pulse);
      setVerse(res.verse);
      setStep(1);
      showToast("Response shared with your circle");
    } catch (e) {
      setError("Submit failed: " + (e as Error).message);
    }
  };

  const loadTomorrow = async () => {
    try {
      setTomorrow(await api.tomorrow(GROUP, date));
      setStep(2);
    } catch (e) {
      setError("Recommendation failed: " + (e as Error).message);
    }
  };

  const runAgain = async () => {
    const next = addDaysIso(date, 1);
    setDate(next);
    resetEngagement();
    setPulse(null);
    setTomorrow(null);
    setStep(0);
    await loadVerse(api, next);
    showToast("Advanced to " + next);
  };

  const demo = true;

  return (
    <div className="wrap">
      <header>
        <div>
          <div className="badge">YouVersion Circle</div>
          <h1>A passage that grows with your group</h1>
          <div className="sub">
            Imagine a world where seeds of faith are planted through small scriptures — and those scriptures grow with you as you discover more. Now imagine doing that in community with your friends and getting to thrive together.
          </div>
        </div>
      </header>

      {error && (
        <div className="callout" role="alert" style={{ borderColor: "rgba(239,68,68,.5)" }}>
          {error}
        </div>
      )}

      <div className="steps">
        {["1 · Read + Engage", "2 · Pulse", "3 · Tomorrow"].map((s, i) => (
          <button
            key={s}
            className={"dot" + (step === i ? " active" : step > i ? " done" : "")}
            onClick={() => setStep(i)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="stage">
        <div className="phone">
          {/* Screen 1: Read + Engage */}
          {step === 0 && verse && (
            <div className="s-verse screen">
              <div className="label">{verse.selection_label}</div>
              <div className="group-name">{config?.group_name}</div>
              <div className="highlight-instruction">Highlight what stands out to you</div>
              <PassageHighlighter text={verse.text} onHighlight={setHighlight} />
              <div className="ref">{verse.citation}</div>
              <div className="glass">
                {engagementPairForDay(GROUP, date).pair === "emotion" ? (
                  <>
                    <div className="label" style={{ opacity: 0.8 }}>How are you feeling?</div>
                    <div className="row">
                      {EMOTION_WORDS.map((w) => (
                        <button
                          key={w}
                          className={"chip" + (reaction === w ? " on" : "")}
                          aria-pressed={reaction === w}
                          onClick={() => setReaction(w)}
                        >
                          {w}
                        </button>
                      ))}
                    </div>
                  </>
                ) : engagementPairForDay(GROUP, date).pair === "reflection" ? (
                  <textarea
                    className="text-input"
                    rows={2}
                    maxLength={500}
                    placeholder={engagementPairForDay(GROUP, date).placeholder}
                    value={reflection}
                    onChange={(e) => setReflection(e.target.value)}
                    aria-label="short reflection"
                  />
                ) : (
                  <input
                    className="text-input"
placeholder="One Word Reflection"
                    value={word}
                    onChange={(e) => setWord(e.target.value.replace(/\s.*/g, ""))}
                    aria-label="one word reflection"
                  />
                )}
              </div>
              <button className="btn cyan" onClick={submit}>
                Reflect to unlock the circle 🔓
              </button>
            </div>
          )}

          {/* Screen 2: named Group Pulse */}
          {step === 1 && pulse && <GroupPulseView pulse={pulse} membersById={membersById} />}
          {step === 1 && (
            demo ? (
              <button className="btn" onClick={loadTomorrow}>See tomorrow's pick →</button>
            ) : null
          )}

          {/* Screen 3: Recommended for Your Group */}
          {step === 2 && tomorrow && (
            <div className="s-tom screen">
              <div className="label">{tomorrow.selection_label}</div>
              <div className="pick">
                <div className="label" style={{ color: "#b45309" }}>Recommended passage</div>
                <div className="verse" style={{ fontSize: 20, color: "#7c2d12" }}>"{tomorrow.text}"</div>
                <div className="ref" style={{ color: "#92400e" }}>{tomorrow.citation}</div>
              </div>
              <div className="phone-title" style={{ marginTop: 12 }}>→ {tomorrow.theme}</div>
              <div className="glass">
                <div className="label" style={{ opacity: 0.8 }}>Why this passage</div>
                <div className="tiny" style={{ marginTop: 6 }}>{tomorrow.explanation}</div>
                {demo && (
                  <ul className="tiny" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                    {tomorrow.signals.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
          {step === 2 && (
            <button className="btn" onClick={runAgain}>Run the loop again ↺</button>
          )}
        </div>

        <div className="panel">
          <div className="step-kicker">
            {["Step 1 · Read + Engage", "Step 2 · Group pulse", "Step 3 · Tomorrow"][step]}
          </div>
          <h2 className="headline">
            {[
              "A passage arrives, chosen for your group.",
              "Group Pulse + AI Synthesis.",
              "Recommended for Your Group.",
            ][step]}
          </h2>
          <div className="copy">
            {[
              "Users will receive a semi-random notification that it is time to engage with Scripture. Using YouVersion's API, a verse is selected and displayed. As individual users engage via a highlight and daily prompt, they can unlock insights across their inner circle.",
              "Responses stay locked until you personally engage. The pulse shows the name of the group, individual responses, and a Gloo AI synthesis of shared needs and ways to support each other.",
              "What's recommended for your group is adaptive, and using Gloo AI it learns from the previous engagement using signals and safeguards.",
            ][step]}
          </div>
          {step === 1 && (
            <div className="callout">
              <div className="label" style={{ fontSize: 13 }}>Why Community Matters</div>
              <ul style={{ margin: "10px 0 0", paddingLeft: 18, lineHeight: 1.9, fontSize: 13, color: "#cbd5e1" }}>
                <li>This is an opportunity to thrive together — Scripture was never meant to be read alone.</li>
                <li>By engaging before seeing others' responses, you practice vulnerability and bring your own honest, unique perspective to the circle.</li>
                <li>AI offers insights and prompts individuals to connect with their circle in meaningful, low-barrier ways.</li>
                <li>Small, consistent touchpoints build relational trust and keep a group spiritually connected between gatherings.</li>
              </ul>
            </div>
          )}
          {step === 0 && (
            <div className="callout">
              <div className="label" style={{ fontSize: 13 }}>Daily Prompts</div>
              <div style={{ marginTop: 8, fontSize: 13, color: "#cbd5e1" }}>
                Each day, the group receives <b>one</b> daily prompt — the same for all members.
              </div>

              <div className="engagement-card">
                <div className="label" style={{ fontSize: 13 }}>Emotion Tap</div>
                <div style={{ marginTop: 4, fontSize: 13, color: "#cbd5e1" }}>How are you feeling?</div>
                <div className="row" style={{ marginTop: 6 }}>
                  {EMOTION_WORDS.map((w) => (
                    <span key={w} className="chip">{w}</span>
                  ))}
                </div>
              </div>

              <div className="engagement-card">
                <div className="label" style={{ fontSize: 13 }}>Short Reflection</div>
                <input className="text-input" readOnly placeholder="What do you hear God saying to you in this verse?" style={{ marginTop: 6 }} />
              </div>

              <div className="engagement-card">
                <div className="label" style={{ fontSize: 13 }}>One Word</div>
                <input className="text-input" readOnly placeholder="One Word Reflection" style={{ marginTop: 6 }} />
              </div>
            </div>
          )}
          {demo && step === 2 && tomorrow?.plan && (
            <div className="callout">
              <RecommendationPlanView plan={tomorrow.plan} />
            </div>
          )}
        </div>
      </div>

      <div className={"toast" + (toast ? " show" : "")}>{toast}</div>
    </div>
  );
}
