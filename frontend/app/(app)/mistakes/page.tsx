"use client";

import { FormEvent, useEffect, useState } from "react";

import { GlassButton, GlassCard, GlassPanel } from "@/components/glass";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type {
  MistakeItem,
  MistakePlan,
  MistakeReflection,
  MistakeResource,
  MistakeReview,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api";

export default function MistakesPage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<MistakeItem[]>([]);
  const [selected, setSelected] = useState<MistakeItem | null>(null);
  const [reflection, setReflection] = useState<MistakeReflection | null>(null);
  const [plan, setPlan] = useState<MistakePlan | null>(null);
  const [resources, setResources] = useState<MistakeResource[]>([]);
  const [review, setReview] = useState<MistakeReview | null>(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    question: "",
    answer: "",
    expected: "",
    concept: "",
  });

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
    load().catch((e: unknown) => setError(getErrorMessage(e)));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const created = await apiJson<MistakeItem>(
        `${API_BASE}/mistakes`,
        auth.access_token,
        {
          method: "POST",
          body: JSON.stringify(form),
        },
      );
      setItems((prev) => [created, ...prev]);
      setForm({ question: "", answer: "", expected: "", concept: "" });
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  }

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

  async function selectMistake(item: MistakeItem) {
    setSelected(item);
    setReflection(readAnalysis<MistakeReflection>(item, "reflection"));
    setPlan(readAnalysis<MistakePlan>(item, "remedial_plan"));
    const pack = readAnalysis<{ resources: MistakeResource[] }>(item, "targeted_resources");
    setResources(pack?.resources ?? []);
    setReview(null);
  }

  async function runAction<T>(path: string, setter: (value: T) => void, init: RequestInit = {}) {
    if (!selected) return;
    setError("");
    try {
      const data = await apiJson<T>(`${API_BASE}${path}`, auth.access_token, init);
      setter(data);
      await load();
    } catch (err: unknown) {
      setError(getErrorMessage(err));
    }
  }

  async function markReviewed() {
    if (!selected) return;
    await runAction<MistakeItem>(
      `/mistakes/${selected.mistake_id}/review`,
      (value) => setSelected(value),
      { method: "PATCH", body: JSON.stringify({ review_status: "reviewed" }) },
    );
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">错题本</h1>
      <GlassPanel className="space-y-4">
        <form className="grid gap-3 md:grid-cols-2" onSubmit={submit}>
          {(["question", "answer", "expected", "concept"] as const).map((field) => (
            <label key={field} className="space-y-1 text-sm text-white/70">
              <span>{labelFor(field)}</span>
              <textarea
                className="min-h-20 w-full resize-y rounded-2xl border border-white/10 bg-white/10 p-3 text-sm text-white outline-none transition focus:border-white/30"
                value={form[field]}
                onChange={(e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))}
                required={field !== "concept"}
              />
            </label>
          ))}
          <div className="md:col-span-2">
            <GlassButton type="submit">记录错题</GlassButton>
          </div>
        </form>
        {error ? <p className="text-sm text-rose-200">{error}</p> : null}
      </GlassPanel>

      {review ? (
        <GlassCard tone="ember" eyebrow="review" title="元认知归因">
          <div className="space-y-3 text-sm text-white/75">
            <p>{review.cause}</p>
            <div className="flex flex-wrap gap-2">
              {review.weakness_tags.map((tag) => (
                <span key={tag} className="rounded-full bg-white/10 px-3 py-1 text-xs">
                  {tag}
                </span>
              ))}
            </div>
            <ol className="list-decimal space-y-1 pl-5">
              {review.review_plan.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </GlassCard>
      ) : null}

      {selected ? (
        <GlassPanel className="space-y-4" tone="mint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase text-cyan-200/80">detail</p>
              <h2 className="mt-1 text-lg font-semibold text-white">{selected.question}</h2>
              <p className="mt-1 text-sm text-white/60">状态：{selected.status}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <GlassButton
                onClick={() =>
                  runAction<MistakeReflection>(
                    `/mistakes/${selected.mistake_id}/reflect`,
                    setReflection,
                    { method: "POST" },
                  )
                }
              >
                归因
              </GlassButton>
              <GlassButton
                onClick={() =>
                  runAction<MistakePlan>(
                    `/mistakes/${selected.mistake_id}/plan`,
                    setPlan,
                    { method: "POST" },
                  )
                }
              >
                计划
              </GlassButton>
              <GlassButton
                onClick={() =>
                  runAction<{ resources: MistakeResource[] }>(
                    `/mistakes/${selected.mistake_id}/resources`,
                    (value) => setResources(value.resources),
                    { method: "POST" },
                  )
                }
              >
                资源
              </GlassButton>
              <GlassButton onClick={markReviewed}>已复习</GlassButton>
            </div>
          </div>

          {reflection ? (
            <GlassCard tone="ember" eyebrow={reflection.category} title="归因结果">
              <p>{reflection.cause}</p>
              <p className="mt-2 text-white/60">{reflection.remedial_goal}</p>
            </GlassCard>
          ) : null}

          {plan ? (
            <GlassCard tone="aurora" eyebrow="path" title="补救计划">
              <ol className="list-decimal space-y-2 pl-5">
                {plan.steps.map((step) => (
                  <li key={step.task_id}>
                    <span className="text-white">{step.objective}</span>
                    <p className="text-xs text-white/55">{step.rationale}</p>
                  </li>
                ))}
              </ol>
            </GlassCard>
          ) : null}

          {resources.length > 0 ? (
            <div className="grid gap-3">
              {resources.map((item) => (
                <GlassCard key={item.resource_id} tone="default" eyebrow={item.type} title={item.title}>
                  <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-xs text-white/70">
                    {item.content}
                  </pre>
                </GlassCard>
              ))}
            </div>
          ) : null}
        </GlassPanel>
      ) : null}

      <div className="grid gap-3">
        {items.map((item) => (
          <GlassCard
            key={item.mistake_id}
            tone={item.status === "reviewed" ? "aurora" : "ember"}
            eyebrow={item.concept || "mistake"}
            title={item.question}
            action={
              <div className="flex gap-2">
                <GlassButton onClick={() => selectMistake(item)}>详情</GlassButton>
                <GlassButton onClick={() => reviewMistake(item.mistake_id)}>旧归因</GlassButton>
              </div>
            }
          >
            <div className="space-y-2 text-sm text-white/70">
              <p>你的答案：{item.answer}</p>
              <p>参考要点：{item.expected}</p>
            </div>
          </GlassCard>
        ))}
      </div>
    </section>
  );
}

function readAnalysis<T>(item: MistakeItem, key: string): T | null {
  const value = item.analysis?.[key];
  return value ? (value as T) : null;
}

function labelFor(field: "question" | "answer" | "expected" | "concept") {
  return {
    question: "题目",
    answer: "你的答案",
    expected: "参考要点",
    concept: "关联概念",
  }[field];
}
