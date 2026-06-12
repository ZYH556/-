"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";

import type { ProfileTrend } from "@/lib/types";

/* mount 下一帧置 true，触发 CSS transition 从初始态生长（同 ProfileGauges.useArmed） */
function useArmed(): boolean {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(raf);
  }, []);
  return armed;
}

const W = 560;
const H = 120;
const PAD_X = 10;
const PAD_Y = 16;

/* 进度火花线：画像快照的 progress 序列。印刷细线 + 空心数据点，
   stroke-dashoffset 从右往左「手绘」入场（与 ProgressRing 同一动效语言）。 */
export function TrendSparkline({ trend }: { trend: ProfileTrend }) {
  const armed = useArmed();
  const pathRef = useRef<SVGPolylineElement>(null);
  const [length, setLength] = useState(0);

  const points = trend.items.map((item, index) => {
    const x =
      trend.items.length === 1
        ? W / 2
        : PAD_X + (index / (trend.items.length - 1)) * (W - PAD_X * 2);
    const y = H - PAD_Y - Math.min(1, Math.max(0, item.progress)) * (H - PAD_Y * 2);
    return { x, y, progress: item.progress, version: item.version };
  });

  useEffect(() => {
    if (pathRef.current) setLength(pathRef.current.getTotalLength());
  }, [trend.items.length]);

  const first = points[0];
  const last = points[points.length - 1];

  return (
    <figure
      role="img"
      aria-label={`画像进度从 ${Math.round(trend.start_progress * 100)}% 到 ${Math.round(trend.latest_progress * 100)}%，共 ${trend.items.length} 份快照`}
    >
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" aria-hidden>
        {/* 印刷基线：上下两条点线界出 0% 与 100% */}
        <line x1={PAD_X} x2={W - PAD_X} y1={PAD_Y} y2={PAD_Y} stroke="var(--ws-line-strong)" strokeWidth="1" strokeDasharray="1 5" />
        <line x1={PAD_X} x2={W - PAD_X} y1={H - PAD_Y} y2={H - PAD_Y} stroke="var(--ws-line-strong)" strokeWidth="1" strokeDasharray="1 5" />
        <polyline
          ref={pathRef}
          points={points.map((p) => `${p.x},${p.y}`).join(" ")}
          fill="none"
          stroke="var(--ws-navy)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={length || undefined}
          strokeDashoffset={length ? (armed ? 0 : length) : undefined}
          style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.15s" }}
        />
        {points.map((p, index) => (
          <circle
            key={`${p.version}-${index}`}
            cx={p.x}
            cy={p.y}
            r="4"
            fill="var(--ws-card)"
            stroke="var(--ws-navy)"
            strokeWidth="2"
            opacity={armed ? 1 : 0}
            style={{ transition: `opacity 0.3s ease ${0.2 + index * 0.08}s` }}
          />
        ))}
      </svg>
      <figcaption className="mt-1 flex items-baseline justify-between text-xs text-slate-500">
        <span>
          首份快照 <span className="ws-serif text-sm text-[var(--ws-ink)]">{Math.round((first?.progress ?? 0) * 100)}%</span>
        </span>
        <span>
          最新 <span className="ws-serif text-sm text-[var(--ws-ink)]">{Math.round((last?.progress ?? 0) * 100)}%</span>
        </span>
      </figcaption>
    </figure>
  );
}

/* 成长对账单：知识点掌握度升降，印刷目录式 leader dots 连接名称与数值 */
export function MasteryLedger({ trend }: { trend: ProfileTrend }) {
  const entries = Object.entries(trend.mastery_delta)
    .sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    .slice(0, 6);

  if (entries.length === 0) {
    return (
      <p className="text-sm leading-6 text-slate-600">
        知识基础还没有跨快照的对比数据。完成几次学习并更新画像后，这里会显示每个知识点的升降。
      </p>
    );
  }

  return (
    <ul className="space-y-2.5">
      {entries.map(([concept, delta]) => (
        <li key={concept} className="flex items-baseline text-sm">
          <span className="shrink-0 font-medium text-[var(--ws-ink)]">{concept}</span>
          <span className="ws-leader mx-2" aria-hidden />
          <DeltaValue delta={delta} />
        </li>
      ))}
    </ul>
  );
}

function DeltaValue({ delta }: { delta: number }) {
  const percent = Math.round(delta * 100);
  if (percent > 0) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 text-[var(--ws-accent)]">
        <ArrowUpRight size={14} aria-hidden />
        <span className="ws-serif text-base">+{percent}%</span>
      </span>
    );
  }
  if (percent < 0) {
    return (
      <span className="inline-flex shrink-0 items-center gap-1 text-amber-600">
        <ArrowDownRight size={14} aria-hidden />
        <span className="ws-serif text-base">{percent}%</span>
      </span>
    );
  }
  return (
    <span className="inline-flex shrink-0 items-center gap-1 text-slate-400">
      <Minus size={14} aria-hidden />
      <span className="ws-serif text-base">持平</span>
    </span>
  );
}

/* 快照不足 2 份：诚实显示收集进度，不伪造趋势 */
export function TrendPlaceholder({ count }: { count: number }) {
  return (
    <div className="border border-dashed border-[var(--ws-line-strong)] px-5 py-6">
      <div className="flex items-center gap-3">
        {[0, 1].map((slot) => (
          <span
            key={slot}
            className={`flex h-9 w-9 items-center justify-center border text-sm font-medium ${
              slot < count
                ? "border-[var(--ws-navy)] bg-[var(--ws-navy)] text-white"
                : "border-dashed border-[var(--ws-line-strong)] text-slate-400"
            }`}
          >
            {slot + 1}
          </span>
        ))}
        <p className="text-sm font-medium text-[var(--ws-ink)]">档案快照收集中 · {Math.min(count, 2)}/2</p>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">
        画像每次发生实质变化都会自动存一份快照。至少两份快照后，这里会画出你的进度曲线和知识点升降对账。
      </p>
    </div>
  );
}
