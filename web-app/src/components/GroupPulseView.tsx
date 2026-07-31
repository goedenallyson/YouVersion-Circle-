import type { GroupPulse, Member } from "../api/types";

interface Props {
  pulse: GroupPulse;
  membersById: Record<string, Member>;
}

export function GroupPulseView({ pulse }: Props) {
  const syn = pulse.synthesis;

  return (
    <div className="s-pulse screen">
      <div className="label">{pulse.group_name}</div>
      <div className="phone-title">Your circle responded</div>

      <div className="glass">
        <div className="tiny" style={{ fontWeight: 800 }}>
          {syn?.headline || (pulse.top_tag ? `${pulse.top_tag} led your circle today` : "Your circle responded")}
        </div>
        <div className="bar"><i style={{ width: `${Math.round((pulse.total_responses / 5) * 100)}%` }} /></div>
        <div className="tiny">{pulse.total_responses} of 5 members responded</div>
        <div className="tiny" style={{ marginTop: 8 }}>{syn?.summary}</div>
      </div>

      <div className="tiny" style={{ marginTop: 12, fontWeight: 800 }}>Who responded</div>
      {pulse.entries.map((e, i) => {
        const bits: string[] = [];
        if (e.highlight) bits.push(`highlighted "${e.highlight}"`);
        if (e.reaction) bits.push(`feeling ${e.reaction}`);
        if (e.word) bits.push(`"${e.word}"`);
        if (e.tag) bits.push(e.tag);
        return (
          <div className="peer" key={i}>
            <div className="av profile-placeholder" />
            <div>
              <b>{e.username || e.member_id || "Member"}</b>
              {bits.length ? " · " + bits.join(" · ") : " · responded"}
              {e.reflection ? <div className="tiny" style={{ opacity: 0.9 }}>&mdash; {e.reflection}</div> : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
