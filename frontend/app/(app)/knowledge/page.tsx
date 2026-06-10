"use client";

import { useEffect, useState } from "react";

import { GlassCard } from "@/components/glass";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { KnowledgeDocument } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api";

export default function KnowledgePage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<KnowledgeDocument[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ items: KnowledgeDocument[] }>(
      `${API_BASE}/knowledge/documents`,
      auth.access_token,
    )
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(getErrorMessage(e)));
  }, [auth.access_token]);

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">个人知识库</h1>
      <GlassCard tone="mint" eyebrow="wave 2" title="私有资料">
        {error ? <p className="text-sm text-rose-200">{error}</p> : null}
        <div className="mt-3 space-y-2">
          {items.length === 0 ? <p>暂无文档。</p> : null}
          {items.map((item) => (
            <div key={item.doc_id} className="rounded-2xl bg-white/10 p-3">
              <p className="font-medium text-white">{item.title}</p>
              <p className="text-xs text-white/50">
                {item.visibility} · {item.format || "unknown"} · {item.course_id || "未归类"}
              </p>
            </div>
          ))}
        </div>
      </GlassCard>
    </section>
  );
}
