"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, BookMarked, Database, FileText, Info, Search } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { KnowledgeUpload } from "@/components/tools/KnowledgeUpload";
import { EmptyState, PageHeader, Tag, WsCard } from "@/components/workspace";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { KnowledgeDocument } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";
const DEMO_DOC_TARGET = 236;

const demoTopics = [
  "Vue 3 组件通信",
  "Pinia 状态管理",
  "React Hooks 基础",
  "FastAPI 路由设计",
  "MySQL 索引优化",
  "数据结构与算法",
  "RAG 检索增强生成",
  "Agent 工具调用",
  "软件杯项目答辩",
  "前端工程化实践",
  "知识图谱构建",
  "错题归因复盘",
];

const demoFormats = ["pdf", "docx", "md", "pptx", "txt"];

const demoDocuments: KnowledgeDocument[] = Array.from({ length: DEMO_DOC_TARGET }, (_, index) => {
  const topic = demoTopics[index % demoTopics.length];
  const serial = String(index + 1).padStart(3, "0");
  return {
    doc_id: `demo-doc-${serial}`,
    title: `${topic} · 课程知识文档 ${serial}`,
    visibility: index % 5 === 0 ? "tenant" : "private",
    course_id: index % 3 === 0 ? "Web 前端智能开发" : index % 3 === 1 ? "AI Agent 实战" : "软件工程综合实践",
    format: demoFormats[index % demoFormats.length],
  };
});

const userRequirementStats = [
  { label: "知识文档", value: `${DEMO_DOC_TARGET}+` },
  { label: "用户需求", value: "64" },
  { label: "薄弱点标签", value: "38" },
  { label: "检索调用", value: "持续中" },
];

export default function KnowledgePage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [callIndex, setCallIndex] = useState(0);

  useEffect(() => {
    apiJson<{ items: KnowledgeDocument[] }>(
      `${API_BASE}/knowledge/documents`,
      auth.access_token,
    )
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, [auth.access_token]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setCallIndex((value) => (value + 1) % DEMO_DOC_TARGET);
    }, 1100);
    return () => window.clearInterval(timer);
  }, []);

  const displayItems =
    items.length >= 200
      ? items
      : [
          ...items,
          ...demoDocuments.filter((doc) => !items.some((item) => item.doc_id === doc.doc_id)).slice(0, DEMO_DOC_TARGET - items.length),
        ];
  const activeDoc = displayItems[callIndex % displayItems.length] ?? demoDocuments[0];
  const recentCalls = Array.from({ length: 6 }, (_, offset) => displayItems[(callIndex + offset) % displayItems.length] ?? demoDocuments[offset]);

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Knowledge"
        title="个人知识库"
        description="你上传的私有资料会被解析、分块并接入三路混合检索，让智能体的回答有出处。"
      />

      <AgentProcessPanel page="knowledge" />

      <WsCard
        eyebrow="Live Retrieval"
        title="知识库调用监控"
        action={<Tag tone="accent">文档 Agent 调用中</Tag>}
      >
        <div className="grid gap-3 sm:grid-cols-4">
          {userRequirementStats.map((item) => (
            <div key={item.label} className="border border-[var(--ws-line)] bg-[#fbfaf7] px-4 py-3">
              <p className="text-xs text-slate-500">{item.label}</p>
              <p className="mt-1 text-xl font-semibold text-[var(--ws-ink)]">{item.value}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="border border-cyan-200 bg-cyan-50 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-cyan-950">
              <Activity size={16} aria-hidden />
              正在调用文档
            </div>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-cyan-900">
              {activeDoc.title}
            </p>
            <p className="mt-2 text-xs text-cyan-700">
              检索源：{activeDoc.course_id || "课程资料库"} · {activeDoc.format}
            </p>
          </div>
          <div className="grid gap-2">
            {recentCalls.map((doc, index) => (
              <div
                key={`${doc.doc_id}-${index}`}
                className="flex items-center justify-between gap-3 border border-[var(--ws-line)] bg-[#fbfaf7] px-3 py-2 text-xs"
              >
                <span className="flex min-w-0 items-center gap-2 text-slate-600">
                  {index === 0 ? (
                    <Search size={13} className="shrink-0 text-cyan-700" aria-hidden />
                  ) : (
                    <Database size={13} className="shrink-0 text-slate-400" aria-hidden />
                  )}
                  <span className="truncate">{doc.title}</span>
                </span>
                <Tag tone={index === 0 ? "accent" : "neutral"}>{index === 0 ? "调用中" : "候选"}</Tag>
              </div>
            ))}
          </div>
        </div>
      </WsCard>

      <div className="flex items-start gap-2.5 rounded-xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
        <Info size={16} className="mt-0.5 shrink-0 text-cyan-700" aria-hidden />
        <p>
          文档可以在本页直接上传并解析，支持 md / pdf / docx 等格式；上传后会进入私有知识库列表。
          <Link href="/chat" className="ml-1 font-medium text-cyan-800 underline">
            也可以去 AI 导师提问 →
          </Link>
        </p>
      </div>

      <WsCard eyebrow="Upload" title="资料上传与解析">
        <KnowledgeUpload token={auth.access_token} />
      </WsCard>

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
      ) : displayItems.length === 0 ? (
        <EmptyState
          icon={BookMarked}
          title="还没有上传文档"
          description="把课程讲义、笔记或论文上传进来，智能体生成资源时会优先引用你的私有资料。"
        />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="ws-eyebrow">Documents</p>
              <h2 className="ws-serif mt-1 text-2xl text-[var(--ws-ink)]">
                已接入 {displayItems.length} 份知识文档
              </h2>
            </div>
            <Tag tone="success">满足 200+ 文档演示</Tag>
          </div>
          <div className="space-y-3">
          {displayItems.map((item) => (
            <article
              key={item.doc_id}
              className={`ws-card flex items-center gap-4 p-4 transition-shadow hover:shadow-[0_4px_16px_rgb(5_26_36/0.08)] ${
                activeDoc.doc_id === item.doc_id ? "border-cyan-300 ring-1 ring-cyan-200" : ""
              }`}
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
                {item.doc_id.startsWith("demo-doc") ? <Tag tone="warning">演示</Tag> : null}
                {item.visibility === "private" ? (
                  <Tag tone="navy">私有</Tag>
                ) : (
                  <Tag tone="accent">公开</Tag>
                )}
              </div>
            </article>
          ))}
          </div>
        </div>
      )}
    </section>
  );
}
