"use client";

import { useEffect, useState } from "react";
import { NotebookPen, Plus, X } from "lucide-react";

import { EmptyState, PageHeader, Tag, WsButton, WsCard } from "@/components/workspace";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type {
  MistakeItem,
  MistakePlan,
  MistakeReflection,
  MistakeResource,
  MistakeReview,
} from "@/lib/types";
import { MistakeDetail, type MistakeAction } from "./MistakeDetail";
import { MistakeForm } from "./MistakeForm";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

export default function MistakesPage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<MistakeItem[]>([]);
  const [selected, setSelected] = useState<MistakeItem | null>(null);
  const [reflection, setReflection] = useState<MistakeReflection | null>(null);
  const [plan, setPlan] = useState<MistakePlan | null>(null);
  const [resources, setResources] = useState<MistakeResource[]>([]);
  const [review, setReview] = useState<MistakeReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [busy, setBusy] = useState<MistakeAction | null>(null);
  const [error, setError] = useState("");

  async function load() {
    const data = await apiJson<{ items: MistakeItem[] }>(
      `${API_BASE}/mistakes`,
      auth.access_token,
    );
    setItems(data.items);
    if (selected) {
      const refreshed = data.items.find((item) => item.mistake_id === selected.mistake_id);
      if (refreshed) setSelected(refreshed);
    }
  }

  useEffect(() => {
    load()
      .catch((e: unknown) => setError(getErrorMessage(e)))
      .finally(() => setLoading(false));
  }, []);

  async function reviewMistake(id: string) {
    setError("");
    try {
      const data = await apiJson<MistakeReview>(
        `${API_BASE}/mistakes/${id}/review`,
        auth.access_token,
        { method: "POST" },
      );
      setReview(data);
      await load();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  }

  function selectMistake(item: MistakeItem) {
    setSelected(item);
    setReflection(readAnalysis<MistakeReflection>(item, "reflection"));
    setPlan(readAnalysis<MistakePlan>(item, "remedial_plan"));
    const pack = readAnalysis<{ resources: MistakeResource[] }>(item, "targeted_resources");
    setResources(pack?.resources ?? []);
    setReview(null);
  }

  async function runAction<T>(
    action: MistakeAction,
    path: string,
    setter: (value: T) => void,
    init: RequestInit = {},
  ) {
    if (!selected) return;
    setBusy(action);
    setError("");
    try {
      const data = await apiJson<T>(`${API_BASE}${path}`, auth.access_token, init);
      setter(data);
      await load();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-8">
      <PageHeader
        eyebrow="Mistakes"
        title="错题本"
        description="记录错题，智能体帮你归因薄弱点、生成补救计划与针对性练习，把每一次出错变成一次进化。"
        actions={
          <WsButton variant="primary" onClick={() => setFormOpen((v) => !v)}>
            {formOpen ? <X size={15} aria-hidden /> : <Plus size={15} aria-hidden />}
            {formOpen ? "收起表单" : "记录错题"}
          </WsButton>
        }
      />

      {formOpen ? (
        <MistakeForm
          onCreated={(created) => {
            setItems((prev) => [created, ...prev]);
            setFormOpen(false);
          }}
          onError={setError}
        />
      ) : null}

      {error ? (
        <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </p>
      ) : null}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 3 }).map((_, i) => <div key={i} className="ws-skeleton h-28" />)
          ) : items.length === 0 ? (
            <EmptyState
              icon={NotebookPen}
              title="还没有错题记录"
              description="点击右上角「记录错题」，写下题目、你的答案与参考要点，开始第一次错因归零。"
            />
          ) : (
            items.map((item) => {
              const active = selected?.mistake_id === item.mistake_id;
              return (
                <button
                  key={item.mistake_id}
                  onClick={() => selectMistake(item)}
                  className={`ws-card w-full p-4 text-left transition-all hover:shadow-[0_4px_16px_rgb(5_26_36/0.08)] ${
                    active ? "border-[var(--ws-navy)] ring-1 ring-[var(--ws-navy)]" : ""
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-1.5">
                    {item.concept ? <Tag tone="navy">{item.concept}</Tag> : null}
                    {item.status === "reviewed" ? (
                      <Tag tone="success">已复习</Tag>
                    ) : (
                      <Tag tone="warning">待复习</Tag>
                    )}
                  </div>
                  <p className="mt-2 line-clamp-2 font-medium text-[var(--ws-ink)]">
                    {item.question}
                  </p>
                  <p className="mt-1 line-clamp-1 text-sm text-slate-500">{item.answer}</p>
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      void reviewMistake(item.mistake_id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.stopPropagation();
                        void reviewMistake(item.mistake_id);
                      }
                    }}
                    className="mt-2.5 inline-block text-xs text-[var(--ws-accent)] hover:underline"
                  >
                    快速归因 →
                  </span>
                </button>
              );
            })
          )}
        </div>

        <div className="space-y-4 lg:sticky lg:top-8">
          {review ? (
            <WsCard eyebrow="Quick Review" title="元认知归因">
              <div className="space-y-3 text-sm text-slate-700">
                <p>{review.cause}</p>
                <div className="flex flex-wrap gap-1.5">
                  {review.weakness_tags.map((tag) => (
                    <Tag key={tag} tone="danger">
                      {tag}
                    </Tag>
                  ))}
                </div>
                <ol className="list-decimal space-y-1 pl-5">
                  {review.review_plan.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
            </WsCard>
          ) : null}

          {selected ? (
            <MistakeDetail
              item={selected}
              reflection={reflection}
              plan={plan}
              resources={resources}
              busy={busy}
              onReflect={() =>
                runAction<MistakeReflection>(
                  "reflect",
                  `/mistakes/${selected.mistake_id}/reflect`,
                  setReflection,
                  { method: "POST" },
                )
              }
              onPlan={() =>
                runAction<MistakePlan>(
                  "plan",
                  `/mistakes/${selected.mistake_id}/plan`,
                  setPlan,
                  { method: "POST" },
                )
              }
              onResources={() =>
                runAction<{ resources: MistakeResource[] }>(
                  "resources",
                  `/mistakes/${selected.mistake_id}/resources`,
                  (value) => setResources(value.resources),
                  { method: "POST" },
                )
              }
              onMarkReviewed={() =>
                runAction<MistakeItem>(
                  "review",
                  `/mistakes/${selected.mistake_id}/review`,
                  (value) => setSelected(value),
                  { method: "PATCH", body: JSON.stringify({ review_status: "reviewed" }) },
                )
              }
            />
          ) : !loading && items.length > 0 ? (
            <EmptyState
              icon={NotebookPen}
              title="从左侧选择一道错题"
              description="选中后可以查看详情，并生成归因分析、补救计划与针对性练习资源。"
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}

function readAnalysis<T>(item: MistakeItem, key: string): T | null {
  const value = item.analysis?.[key];
  return value ? (value as T) : null;
}
