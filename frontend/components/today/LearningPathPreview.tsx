import { Check, CircleDot, MoveRight } from "lucide-react";

import type { LearningPathNode } from "./types";

type LearningPathPreviewProps = {
  phase: string;
  progress: number;
  nodes: LearningPathNode[];
  recommendation: string;
};

const STATUS_LABEL: Record<LearningPathNode["status"], string> = {
  done: "已完成",
  current: "当前节点",
  next: "下一节点",
};

export function LearningPathPreview({
  phase,
  progress,
  nodes,
  recommendation,
}: LearningPathPreviewProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ws-accent)]">
            Learning Path
          </p>
          <h2 className="mt-2 text-xl font-medium text-[var(--ws-ink)]">{phase}</h2>
        </div>
        <div className="w-full sm:w-56">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>路径进度</span>
            <span>{progress}%</span>
          </div>
          <div className="mt-2 h-1.5 bg-[#e7e3da]">
            <div className="h-full bg-[#0e7490]" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {nodes.map((node, index) => (
          <article key={node.id} className="relative bg-white px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <span className="inline-flex h-8 w-8 items-center justify-center bg-[#f0eee7] text-[var(--ws-ink)]">
                {node.status === "done" ? (
                  <Check size={16} aria-hidden />
                ) : node.status === "current" ? (
                  <CircleDot size={16} aria-hidden />
                ) : (
                  <MoveRight size={16} aria-hidden />
                )}
              </span>
              <span className="text-xs text-slate-500">{STATUS_LABEL[node.status]}</span>
            </div>
            <h3 className="mt-4 text-base font-medium text-[var(--ws-ink)]">{node.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">{node.summary}</p>
            {index < nodes.length - 1 ? (
              <span
                className="absolute -right-2 top-1/2 hidden h-px w-4 bg-[var(--ws-line-strong)] lg:block"
                aria-hidden
              />
            ) : null}
          </article>
        ))}
      </div>

      <p className="border-l-2 border-[#0e7490] pl-4 text-sm leading-6 text-slate-600">
        推荐理由：{recommendation}
      </p>
    </section>
  );
}
