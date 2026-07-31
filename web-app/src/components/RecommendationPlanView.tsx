import type { RecommendationPlan } from "../api/types";

export function RecommendationPlanView({ plan }: { plan: RecommendationPlan }) {
  return (
    <>
      <div className="glass">
        <div className="label" style={{ opacity: 0.8, fontSize: 13 }}>Workflow</div>
        <ol style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13, color: "#cbd5e1", lineHeight: 1.9 }}>
          {plan.workflow.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ol>
      </div>
      <div className="glass">
        <div className="label" style={{ opacity: 0.8, fontSize: 13 }}>Signals &amp; weighting</div>
        <div style={{ marginTop: 8, lineHeight: 1.7, fontSize: 13, color: "#cbd5e1" }}>
          {plan.signals.map((s) => (
            <div key={s.signal} style={{ opacity: s.present ? 1 : 0.45 }} title={s.note}>
              {s.present ? "✓" : "–"} {s.signal}{" "}
              <span className={`strength ${s.strength}`}>[{s.strength}]</span>
            </div>
          ))}
        </div>
      </div>
      <div className="glass">
        <div className="label" style={{ opacity: 0.8, fontSize: 13 }}>Safeguards</div>
        <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13, color: "#cbd5e1", lineHeight: 1.9 }}>
          {plan.safeguards_applied.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      </div>
    </>
  );
}
