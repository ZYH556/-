"use client";

import { FormEvent, useState } from "react";

import { WsButton, WsCard } from "@/components/workspace";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { MistakeItem } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

const FIELD_LABELS = {
  question: "题目",
  answer: "你的答案",
  expected: "参考要点",
  concept: "关联概念",
} as const;

type FieldKey = keyof typeof FIELD_LABELS;

const EMPTY_FORM: Record<FieldKey, string> = {
  question: "",
  answer: "",
  expected: "",
  concept: "",
};

interface MistakeFormProps {
  onCreated: (item: MistakeItem) => void;
  onError: (message: string) => void;
}

export function MistakeForm({ onCreated, onError }: MistakeFormProps) {
  const { auth } = useAuthSession();
  const [form, setForm] = useState(EMPTY_FORM);

  async function submit(e: FormEvent) {
    e.preventDefault();
    onError("");
    try {
      const created = await apiJson<MistakeItem>(`${API_BASE}/mistakes`, auth.access_token, {
        method: "POST",
        body: JSON.stringify(form),
      });
      setForm(EMPTY_FORM);
      onCreated(created);
    } catch (err: unknown) {
      onError(getErrorMessage(err));
    }
  }

  return (
    <WsCard title="记录一道错题">
      <form className="grid gap-3 md:grid-cols-2" onSubmit={submit}>
        {(Object.keys(FIELD_LABELS) as FieldKey[]).map((field) => (
          <label key={field} className="space-y-1.5 text-sm text-slate-600">
            <span>{FIELD_LABELS[field]}</span>
            <textarea
              className="min-h-20 w-full resize-y rounded-xl border border-[var(--ws-line)] bg-white p-3 text-sm text-[var(--ws-ink)] outline-none transition-colors focus:border-[var(--ws-navy)]"
              value={form[field]}
              onChange={(e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))}
              required={field !== "concept"}
            />
          </label>
        ))}
        <div className="md:col-span-2">
          <WsButton type="submit" variant="primary">
            保存错题
          </WsButton>
        </div>
      </form>
    </WsCard>
  );
}
