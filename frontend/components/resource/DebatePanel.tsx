import type { DebateRound, JudgeVerdict } from "@/lib/types";

export function DebatePanel({
  rounds,
  verdict,
}: {
  rounds: DebateRound[];
  verdict: JudgeVerdict | null;
}) {
  if (rounds.length === 0 && !verdict) return null;

  return (
    <section className="rounded-xl border border-rose-200 bg-rose-50 p-4">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-rose-600">
        多智能体辩论
      </h2>
      {rounds.map((r) => (
        <div key={r.round} className="mb-2 text-sm">
          <div className="font-medium text-slate-700">第 {r.round} 轮</div>
          <ul className="ml-4 list-disc text-slate-600">
            {r.positions.map((p, i) => (
              <li key={i}>
                <span className="font-medium">{p.perspective || "观点"}</span>：
                {p.claim}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {verdict && (
        <div className="mt-2 rounded-lg bg-white p-3 text-sm shadow-sm">
          <div className="font-semibold text-rose-700">
            裁决：{verdict.winner_position}
          </div>
          <div className="mt-1 text-slate-600">{verdict.reasoning}</div>
          <div className="mt-1 text-xs text-slate-400">
            置信度 {Math.round((verdict.confidence || 0) * 100)}%
          </div>
        </div>
      )}
    </section>
  );
}
