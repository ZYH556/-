"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Check, CircleDot, MoveRight, Pin } from "lucide-react";

import { updatePlanItemStatus } from "@/lib/planApi";
import { WsCard } from "@/components/workspace";
import { viewForResource } from "@/components/resource/resourceView";
import type { TodayLearningPathNode } from "@/lib/types";

interface PlanTimelineProps {
  nodes: TodayLearningPathNode[];
  progress: number;
  recommendation: string;
  token?: string;
  onChanged?: () => void;
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

/* 学习路径 = 行程单（Itinerary）：铅字序号 + 状态印章 + 点线行程线。
   真实路径节点（item_id 非空）可直接标记完成——进度与画像随之联动。 */
export function PlanTimeline({ nodes, progress, recommendation, token, onChanged }: PlanTimelineProps) {
  const percent = Math.min(100, Math.max(0, Math.round(progress * 100)));
  const [savingId, setSavingId] = useState<number | null>(null);

  const markDone = async (itemId: number) => {
    // 凭据走 HttpOnly cookie，token 生产为空串，不作为可用性判据；apiJson 自带 cookie
    if (savingId !== null) return;
    setSavingId(itemId);
    try {
      await updatePlanItemStatus(token ?? "", itemId, "done");
      onChanged?.();
    } catch {
      /* 失败保持原状态，用户可重试 */
    } finally {
      setSavingId(null);
    }
  };

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
          const actionable = Boolean(node.item_id && !isDone);
          return (
            <li
              key={node.id}
              className="ws-rise relative grid grid-cols-[56px_1fr] gap-x-4 pb-7 last:pb-0 sm:grid-cols-[64px_1fr]"
              style={{ animationDelay: `${index * 80}ms` }}
            >
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
                {node.resources && node.resources.length > 0 ? (
                  <div className="mt-3 border-t border-dashed border-[var(--ws-line)] pt-3">
                    <p className="text-xs text-slate-400">这一步可以看</p>
                    <ul className="mt-1.5 space-y-1.5">
                      {node.resources.map((res) => {
                        const ResIcon = viewForResource(res.type ?? "").icon;
                        return (
                          <li key={res.resource_id}>
                            <Link
                              href={`/resources/${encodeURIComponent(res.resource_id)}`}
                              className="inline-flex items-center gap-1.5 text-sm text-[var(--ws-accent)] hover:text-[var(--ws-ink)]"
                            >
                              {res.pinned ? (
                                <Pin size={12} className="shrink-0" aria-label="已固定" />
                              ) : (
                                <ResIcon size={13} aria-hidden />
                              )}
                              <span className="line-clamp-1">{res.title}</span>
                              <ArrowUpRight size={12} className="shrink-0" aria-hidden />
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : null}
                {actionable ? (
                  <button
                    type="button"
                    onClick={() => markDone(node.item_id as number)}
                    disabled={savingId !== null}
                    className="mt-3 inline-flex items-center gap-1.5 border border-[var(--ws-line-strong)] bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-[var(--ws-accent)] hover:text-[var(--ws-accent)] disabled:opacity-50"
                  >
                    <Check size={13} aria-hidden />
                    {savingId === node.item_id ? "保存中…" : "标记完成"}
                  </button>
                ) : null}
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
