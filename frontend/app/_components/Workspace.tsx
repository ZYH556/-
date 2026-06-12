"use client";

import type { ReactNode } from "react";
import type { CurrentUser } from "@/lib/types";
import { useChat } from "@/lib/useChat";
import { ChatInput } from "@/components/chat/ChatInput";
import { AgentTimeline } from "@/components/resource/AgentTimeline";
import { ResourceCard } from "@/components/resource/ResourceCard";
import { DebatePanel } from "@/components/resource/DebatePanel";
import { LearningPathCard } from "@/components/resource/LearningPathCard";
import { KnowledgeUpload } from "@/components/tools/KnowledgeUpload";
import { VideoJobCard } from "@/components/tools/VideoJobCard";

interface WorkspaceProps {
  token: string;
  user: CurrentUser;
  onLogout: () => void;
  embedded?: boolean;
  emptyState?: ReactNode;
  showTools?: boolean;
  actionBar?: (args: {
    disabled: boolean;
    onSelect: (message: string, displayMessage?: string) => void;
  }) => ReactNode;
}

export function Workspace({
  token,
  user,
  onLogout,
  embedded = false,
  emptyState,
  actionBar,
  showTools = true,
}: WorkspaceProps) {
  const { turns, send, stop, resetSession, streaming } = useChat(token);

  return (
    <main
      className={
        embedded
          ? "flex flex-col gap-6"
          : "mx-auto flex min-h-screen max-w-3xl flex-col gap-6 px-4 py-8"
      }
    >
      {embedded ? (
        turns.length > 0 && (
          <div className="flex justify-end">
            <button
              onClick={resetSession}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-indigo-400 hover:text-indigo-600"
            >
              新会话
            </button>
          </div>
        )
      ) : (
        <header className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">ReflexLearn</h1>
            <p className="mt-1 text-sm text-slate-500">
              多智能体个性化学习系统 · 多轮对话，记忆贯通
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <div className="hidden text-right text-xs text-slate-500 sm:block">
              <div className="font-medium text-slate-700">{user.user_id}</div>
              <div>
                {user.tenant_id} · {user.role}
              </div>
            </div>
            {turns.length > 0 && (
              <button
                onClick={resetSession}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-indigo-400 hover:text-indigo-600"
              >
                新会话
              </button>
            )}
            <button
              onClick={onLogout}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-rose-400 hover:text-rose-600"
            >
              退出
            </button>
          </div>
        </header>
      )}

      {showTools ? (
        <details className="rounded-xl border border-slate-200 bg-white">
          <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-slate-700">
            知识库上传 & 视频生成
          </summary>
          <div className="space-y-4 border-t border-slate-100 p-4">
            <KnowledgeUpload token={token} />
            <VideoJobCard token={token} />
          </div>
        </details>
      ) : null}

      <div className="space-y-2">
        <ChatInput disabled={streaming} onSend={send} />
        {actionBar ? actionBar({ disabled: streaming, onSelect: send }) : null}
        {streaming && (
          <button
            onClick={stop}
            className="text-xs font-medium text-slate-500 underline transition hover:text-rose-600"
          >
            停止生成
          </button>
        )}
      </div>

      {turns.length === 0 && (
        emptyState ?? (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400">
            输入一个学习目标开始，例如「线性回归」或「机器学习从入门到精通的系统学习路径」。
            支持多轮追问，Agent 会记住上下文。
          </div>
        )
      )}

      <div className="space-y-8">
        {turns.map((turn) => {
          const cards = Array.from(turn.cards.values());
          const isStreaming = turn.status === "streaming";
          return (
            <section key={turn.id} className="space-y-4">
              <div className="flex justify-end">
                <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-sm text-white shadow-sm">
                  {turn.userMessage}
                </div>
              </div>

              {turn.error && (
                <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                  出错了：{turn.error}
                </div>
              )}

              <AgentTimeline steps={turn.steps} streaming={isStreaming} />

              <DebatePanel rounds={turn.debateRounds} verdict={turn.verdict} />

              {turn.path && <LearningPathCard path={turn.path} />}

              {cards.length > 0 && (
                <div className="space-y-4">
                  <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    学习资源（{cards.length}）
                  </h2>
                  {cards.map((c) => (
                    <ResourceCard key={c.task_id} card={c} />
                  ))}
                </div>
              )}
            </section>
          );
        })}
      </div>
    </main>
  );
}
