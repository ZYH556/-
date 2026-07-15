"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, FolderOpen, LayoutGrid, Plus } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { EmptyState, PageHeader, Tag, WsButton, type TagTone } from "@/components/workspace";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { LearningSpace, SpaceDetail } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

function statusMeta(status: string): { tone: TagTone; label: string } {
  if (status === "active") return { tone: "success", label: "进行中" };
  if (status === "archived") return { tone: "neutral", label: "已归档" };
  if (status === "done" || status === "completed") return { tone: "accent", label: "已完成" };
  return { tone: "neutral", label: status || "未知" };
}

export default function SpacesPage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<LearningSpace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const reload = useCallback(() => {
    apiJson<{ items: LearningSpace[] }>(`${API_BASE}/spaces`, auth.access_token)
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [auth.access_token]);

  useEffect(() => {
    reload();
  }, [reload]);

  const createSpace = async () => {
    const trimmed = title.trim();
    if (!trimmed || submitting) return;
    setSubmitting(true);
    try {
      await apiJson<SpaceDetail>(`${API_BASE}/spaces`, auth.access_token, {
        method: "POST",
        body: JSON.stringify({ title: trimmed }),
      });
      setTitle("");
      setCreating(false);
      reload();
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Spaces"
        title="学习空间"
        description="按学习目标组织你的资料、资源与路径。每完成一个目标，这里会多一份可回看的学习资产。"
        actions={
          <WsButton variant="primary" onClick={() => setCreating((v) => !v)}>
            <span className="inline-flex items-center gap-1.5">
              <Plus size={15} aria-hidden /> 新建学习目标
            </span>
          </WsButton>
        }
      />

      <AgentProcessPanel page="spaces" />

      {creating ? (
        <div className="ws-card flex flex-wrap items-center gap-3 p-4">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createSpace()}
            placeholder="例如：两周掌握机器学习基础"
            className="min-w-0 flex-1 rounded-xl border border-[var(--ws-line-strong)] bg-white px-3.5 py-2.5 text-sm text-[var(--ws-ink)] outline-none placeholder:text-slate-400 focus:border-[var(--ws-navy)]"
            autoFocus
          />
          <WsButton variant="primary" onClick={createSpace} disabled={submitting || !title.trim()}>
            {submitting ? "创建中…" : "创建"}
          </WsButton>
        </div>
      ) : null}

      {error ? (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="ws-skeleton h-28" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={LayoutGrid}
          title="还没有学习空间"
          description="新建一个学习目标，或从一次对话开始：智能体生成的路径与资源会自动归入对应的学习空间。"
          action={
            <WsButton variant="primary" onClick={() => setCreating(true)}>
              <span className="inline-flex items-center gap-1.5">
                <Plus size={15} aria-hidden /> 新建学习目标
              </span>
            </WsButton>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => {
            const status = statusMeta(item.status);
            return (
              <Link
                key={item.space_id}
                href={`/spaces/${item.space_id}`}
                className="ws-card group block p-5 transition-shadow hover:shadow-[0_4px_16px_rgb(5_26_36/0.08)]"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[rgb(5_26_36/0.05)] text-slate-500">
                    <FolderOpen size={17} aria-hidden />
                  </span>
                  <Tag tone={status.tone}>{status.label}</Tag>
                </div>
                <h3 className="mt-3 font-medium text-[var(--ws-ink)]">{item.title}</h3>
                <span className="mt-2 inline-flex items-center gap-1 text-xs text-slate-400 transition-colors group-hover:text-cyan-700">
                  打开空间 <ArrowRight size={12} aria-hidden />
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
