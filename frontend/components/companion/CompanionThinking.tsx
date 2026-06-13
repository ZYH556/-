"use client";

import { useEffect, useState } from "react";

/* 等待中间态：tutor/ask 是一次性 HTTP（非流式），真实 LLM 可能 3s~75s。
   按等待时长给诚实的阶段性文案——不假装知道后端进度，但让用户知道没挂。 */
const PHASES: Array<{ afterMs: number; text: string }> = [
  { afterMs: 0, text: "正在理解你的问题…" },
  { afterMs: 2500, text: "正在结合你的画像与当前页面整理思路…" },
  { afterMs: 7000, text: "仍在整理答案，复杂问题会多花一点时间…" },
  { afterMs: 16000, text: "回答还在生成，再等等；也可以稍后换个问法重问。" },
];

export function CompanionThinking() {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const timers = PHASES.slice(1).map((item, index) =>
      window.setTimeout(() => setPhase(index + 1), item.afterMs),
    );
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  return (
    <div className="flex max-w-[85%] items-center gap-2.5 rounded-xl bg-[rgb(5_26_36/0.04)] px-3.5 py-2.5">
      <span className="flex shrink-0 items-end gap-1" aria-hidden>
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--ws-accent)]"
            style={{ animationDelay: `${dot * 150}ms`, animationDuration: "0.9s" }}
          />
        ))}
      </span>
      <p className="text-sm leading-relaxed text-slate-500" role="status" aria-live="polite">
        {PHASES[phase].text}
      </p>
    </div>
  );
}
