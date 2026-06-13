"use client";

import { Check, CircleDot, MoveRight } from "lucide-react";

import { WsCard } from "@/components/workspace";
import type { TodayLearningPathNode } from "@/lib/types";

interface PlanTimelineProps {
  nodes: TodayLearningPathNode[];
  progress: number;
  recommendation: string;
}

const STATUS_META: Record<
  TodayLearningPathNode["status"],
  { label: string; stampClass: string }
> = {
  done: { label: "已完成", stampClass: "text-[var(--ws-accent)]" },
  current: { label: "进行中", stampClass: "text-[var(--ws-ink)]" },
  next: { label: "待开始", stampClass: "text-slate-400" },
};

function StatusIcon({ status }: { status: TodayLearningPathNode["status"] }) {
  if (status === "done") return <Check size={15} aria-hidden />;
  if (status === "current") return <CircleDot size={15} aria-hidden />;
  return <MoveRight size={15} aria-hidden />;
}

/* 学习路径 = 行程单（Itinerary）：铅字序号 + 状态印章 + 点线行程线，
   与 /profile 的「学习档案」同一印刷语言。 */
export function PlanTimeline({ nodes, progress, recommendation }: PlanTimelineProps) {
  const percent = Math.min(100, Math.max(0, Math.round(progress * 100)));

  return (
    <WsCard title="当前学习路径" eyebrow="Itinerary">
      <div className="mb-7">
        <div className="flex items-baseline justify-between text-xs text-slate-500">
          <span>路径推进</span>
          <span className="ws-serif text-base text-[var(--ws-ink)]">{percent}%</span>
        </div>
        <div
          className="ws-ticks mt-2 h-3.5"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-label={`路径推进 ${percent}%`}
        >
          <div className="h-full bg-[var(--ws-navy)]" style={{ width: `${percent}%` }} />
        </div>
      </div>

      <ol>
        {nodes.map((node, index) => {
          const meta = STATUS_META[node.status];
          const isCurrent = node.status === "current";
          const isDone = node.status === "done";
          return (
            <li
              key={node.id}
              className="ws-rise relative grid grid-cols-[56px_1fr] gap-x-4 pb-7 last:pb-0 sm:grid-cols-[64px_1fr]"
              style={{ animationDelay: `${index * 80}ms` }}
            >
              {/* 行程线：点线垂直贯穿，已完成段实线 */}
              {index < nodes.length - 1 ? (
                <span
                  aria-hidden
                  className={`absolute left-[27px] top-12 bottom-1 w-px sm:left-[31px] ${
                    isDone
                      ? "bg-[var(--ws-accent)] opacity-50"
                      : "border-l-2 border-dotted border-[var(--ws-line-strong)]"
                  }`}
                />
              ) : null}

              <div className="relative flex flex-col items-center">
                <span
                  className={`flex h-10 w-10 items-center justify-center border sm:h-[42px] sm:w-[42px] ${
                    isCurrent
                      ? "border-[var(--ws-navy)] bg-[var(--ws-navy)] text-white"
                      : isDone
                        ? "border-[var(--ws-accent)] bg-white text-[var(--ws-accent)]"
                        : "border-dashed border-[var(--ws-line-strong)] bg-white text-slate-400"
                  }`}
                >
                  <StatusIcon status={node.status} />
                </span>
                <span className="ws-serif mt-1.5 text-xs tracking-[0.14em] text-slate-400">
                  №{String(index + 1).padStart(2, "0")}
                </span>
              </div>

              <article
                className={`border bg-white p-4 ${
                  isCurrent
                    ? "border-[var(--ws-navy)] shadow-[0_2px_8px_rgb(5_26_36/0.08)]"
                    : "border-[var(--ws-line)]"
                }`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3
                    className={`font-medium leading-6 ${
                      node.status === "next" ? "text-slate-500" : "text-[var(--ws-ink)]"
                    }`}
                  >
                    {node.title}
                  </h3>
                  <span className={`ws-stamp ${meta.stampClass}`}>{meta.label}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600">{node.summary}</p>
              </article>
            </li>
          );
        })}
      </ol>

      <p className="mt-7 border-t border-dashed border-[var(--ws-line-strong)] pt-4 text-sm leading-6 text-slate-600">
        <span className="ws-eyebrow mr-2">Why</span>
        推荐理由：{recommendation}
      </p>
    </WsCard>
  );
}
