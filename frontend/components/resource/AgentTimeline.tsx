import type { AgentStep } from "@/lib/types";

const STEP_LABEL: Record<string, string> = {
  session_start: "会话开始",
  profile: "构建学习画像",
  planner: "规划资源任务",
  gate: "验收裁决",
  critic: "失败归因 / 重规划",
  pipeline: "流水线协作生成",
  assemble: "组装资源包",
  path_plan: "规划学习路径",
};

export function AgentTimeline({
  steps,
  streaming,
}: {
  steps: AgentStep[];
  streaming: boolean;
}) {
  if (steps.length === 0 && !streaming) return null;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
        Agent 协作过程
      </h2>
      <ol className="space-y-2">
        {steps.map((s, i) => (
          <li key={i} className="flex items-start gap-3 text-sm">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-medium text-indigo-700">
              {i + 1}
            </span>
            <div className="leading-5">
              <span className="font-medium text-slate-800">
                {STEP_LABEL[s.step] || s.step}
              </span>
              {(s.detail || s.message) && (
                <span className="ml-2 text-slate-500">{s.detail || s.message}</span>
              )}
            </div>
          </li>
        ))}
        {streaming && (
          <li className="flex items-center gap-3 text-sm text-slate-400">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center">
              <span className="h-2 w-2 animate-ping rounded-full bg-indigo-400" />
            </span>
            处理中…
          </li>
        )}
      </ol>
    </section>
  );
}
