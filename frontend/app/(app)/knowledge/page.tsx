"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookMarked, FileText, Info } from "lucide-react";

import { EmptyState, PageHeader, Tag } from "@/components/workspace";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { KnowledgeDocument } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export default function KnowledgePage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ items: KnowledgeDocument[] }>(
      `${API_BASE}/knowledge/documents`,
      auth.access_token,
    )
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [auth.access_token]);

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Knowledge"
        title="个人知识库"
        description="你上传的私有资料会被解析、分块并接入三路混合检索，让智能体的回答有出处。"
      />

      <div className="flex items-start gap-2.5 rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
        <Info size={16} className="mt-0.5 shrink-0 text-cyan-700" aria-hidden />
        <p>
          文档通过 AI 学习导师的资料入口上传并解析，支持 md / pdf / docx 等格式。
          <Link href="/chat" className="ml-1 font-medium text-cyan-800 underline">
            去上传 →
          </Link>
        </p>
      </div>

      {error ? (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="ws-skeleton h-16" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={BookMarked}
          title="还没有上传文档"
          description="把课程讲义、笔记或论文上传进来，智能体生成资源时会优先引用你的私有资料。"
        />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article
              key={item.doc_id}
              className="ws-card flex items-center gap-4 p-4 transition-shadow hover:shadow-[0_4px_16px_rgb(5_26_36/0.08)]"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-sky-100 text-sky-800">
                <FileText size={18} aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-medium text-[var(--ws-ink)]">
                  {item.title}
                </h3>
                <p className="mt-0.5 text-xs text-slate-500">
                  {item.course_id || "未归类"}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <Tag tone="neutral">{item.format || "unknown"}</Tag>
                {item.visibility === "private" ? (
                  <Tag tone="navy">私有</Tag>
                ) : (
                  <Tag tone="accent">公开</Tag>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
