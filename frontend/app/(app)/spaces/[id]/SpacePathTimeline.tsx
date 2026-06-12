import { CheckCircle2, CircleDashed, PlayCircle } from "lucide-react";

import { Tag, resourceMeta } from "@/components/workspace";
import type { SpacePathStep } from "@/lib/types";

function difficultyLabel(d: number): string {
  if (d <= 0.3) return "入门";
  if (d <= 0.55) return "进阶";
  return "挑战";
}

function StepIcon({ status }: { status: string }) {
  if (status === "done")
    return <CheckCircle2 size={18} className="text-emerald-600" aria-hidden />;
  if (status === "in_progress")
    return <PlayCircle size={18} className="text-cyan-700" aria-hidden />;
  return <CircleDashed size={18} className="text-slate-300" aria-hidden />;
}

export function SpacePathTimeline({ steps }: { steps: SpacePathStep[] }) {
  return (
    <ol className="relative space-y-1">
      {steps.map((step, idx) => {
        const meta = resourceMeta(step.resource_type);
        const active = step.mastery_status === "in_progress";
        return (
          <li key={`${step.sequence}-${step.task_ref}`} className="relative flex gap-3">
            <div className="flex flex-col items-center">
              <StepIcon status={step.mastery_status} />
              {idx < steps.length - 1 ? (
                <span className="w-px flex-1 bg-[var(--ws-line)]" aria-hidden />
              ) : null}
            </div>
            <div
              className={`mb-3 min-w-0 flex-1 rounded-xl border p-3.5 ${
                active
                  ? "border-cyan-300 bg-cyan-50/60"
                  : "border-[var(--ws-line)] bg-white"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-slate-400">
                  {String(step.sequence).padStart(2, "0")}
                </span>
                <h4 className="font-medium text-[var(--ws-ink)]">
                  {step.concept || step.task_ref}
                </h4>
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${meta.chipClass}`}
                >
                  {meta.label}
                </span>
                <Tag tone={step.difficulty > 0.55 ? "warning" : "neutral"}>
                  {difficultyLabel(step.difficulty)}
                </Tag>
                {active ? <Tag tone="accent">当前位置</Tag> : null}
              </div>
              {step.objective ? (
                <p className="mt-1.5 text-sm text-slate-700">{step.objective}</p>
              ) : null}
              {step.rationale ? (
                <p className="mt-1 text-xs leading-relaxed text-slate-500">
                  为什么是这一步：{step.rationale}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
