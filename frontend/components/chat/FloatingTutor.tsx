"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { GraduationCap, Send, X } from "lucide-react";

import { apiJson } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import { workspaceNavItems } from "@/lib/nav";
import type { TutorReply } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

interface TutorTurn {
  role: "user" | "tutor";
  text: string;
  degraded?: boolean;
}

function pageLabel(pathname: string): string {
  const hit = workspaceNavItems.find((item) => pathname.startsWith(item.href));
  return hit ? hit.label : "当前页面";
}

/**
 * 旧版圆形按钮浮窗，已被 components/companion/LearningCompanion 取代，
 * 保留备查，不再挂载为入口。
 */
export function FloatingTutor() {
  const { auth } = useAuthSession();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<TutorTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [turns, open]);

  const ask = async () => {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setTurns((t) => [...t, { role: "user", text: question }]);
    setBusy(true);
    try {
      const reply = await apiJson<TutorReply>(`${API_BASE}/tutor/ask`, auth.access_token, {
        method: "POST",
        body: JSON.stringify({
          question,
          context_hint: `用户正在「${pageLabel(pathname)}」页面提问`,
        }),
      });
      const text = reply.blocked
        ? "这个问题被安全策略拦截了，换个学习相关的问法试试。"
        : reply.answer;
      setTurns((t) => [...t, { role: "tutor", text, degraded: reply.degraded }]);
    } catch {
      setTurns((t) => [...t, { role: "tutor", text: "网络异常，稍后再试一次。", degraded: true }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end gap-3">
      {open ? (
        <div className="flex h-[480px] w-[min(92vw,360px)] flex-col overflow-hidden rounded-2xl border border-[var(--ws-line-strong)] bg-white shadow-[0_12px_40px_rgb(5_26_36/0.18)]">
          <header className="flex items-center justify-between border-b border-[var(--ws-line)] bg-[#051A24] px-4 py-3 text-white">
            <div className="flex items-center gap-2">
              <GraduationCap size={16} aria-hidden />
              <span className="text-sm font-medium">AI 导师 · 即时答疑</span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-lg p-1 text-white/70 hover:bg-white/10 hover:text-white"
              aria-label="关闭辅导窗口"
            >
              <X size={15} aria-hidden />
            </button>
          </header>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {turns.length === 0 ? (
              <div className="rounded-xl bg-[rgb(5_26_36/0.04)] px-3.5 py-3 text-sm leading-relaxed text-slate-600">
                学习中遇到卡点随时问我：概念解释、题目思路、代码报错都可以。
                我会结合你的画像和当前页面给针对性解答。
              </div>
            ) : (
              turns.map((t, i) => (
                <div
                  key={i}
                  className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    t.role === "user"
                      ? "ml-auto bg-[var(--ws-navy)] text-white"
                      : "bg-[rgb(5_26_36/0.04)] text-slate-700"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">{t.text}</p>
                  {t.degraded ? (
                    <p className="mt-1 text-[11px] text-amber-600">离线降级回答</p>
                  ) : null}
                </div>
              ))
            )}
            {busy ? <div className="ws-skeleton h-10 w-2/3" /> : null}
          </div>

          <div className="flex items-end gap-2 border-t border-[var(--ws-line)] p-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  ask();
                }
              }}
              rows={1}
              placeholder="例如：为什么我的梯度下降不收敛？"
              className="max-h-24 min-w-0 flex-1 resize-none rounded-xl border border-[var(--ws-line-strong)] bg-white px-3 py-2 text-sm text-[var(--ws-ink)] outline-none placeholder:text-slate-400 focus:border-[var(--ws-navy)]"
            />
            <button
              type="button"
              onClick={ask}
              disabled={busy || !input.trim()}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--ws-navy)] text-white transition-opacity hover:opacity-90 disabled:opacity-40"
              aria-label="发送问题"
            >
              <Send size={15} aria-hidden />
            </button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--ws-navy)] text-white shadow-[0_8px_24px_rgb(5_26_36/0.3)] transition-transform hover:scale-105"
        aria-label={open ? "收起 AI 导师" : "打开 AI 导师即时答疑"}
      >
        {open ? <X size={20} aria-hidden /> : <GraduationCap size={20} aria-hidden />}
      </button>
    </div>
  );
}
