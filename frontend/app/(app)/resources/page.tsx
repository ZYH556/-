"use client";

import { useEffect, useState } from "react";

import { GlassCard } from "@/components/glass";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { LearningResource } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api";

export default function ResourcesPage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<LearningResource[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<{ items: LearningResource[] }>(`${API_BASE}/resources`, auth.access_token)
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(getErrorMessage(e)));
  }, [auth.access_token]);

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">资源库</h1>
      <GlassCard tone="aurora" eyebrow="wave 2" title="已生成资源管理">
        {error ? <p className="text-sm text-rose-200">{error}</p> : null}
        <div className="mt-3 space-y-2">
          {items.length === 0 ? <p>暂无资源。</p> : null}
          {items.map((item) => (
            <div key={item.resource_id} className="rounded-2xl bg-white/10 p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="font-medium text-white">{item.title || item.type}</p>
                <span className="rounded-full bg-white/10 px-2 py-1 text-xs text-white/60">
                  {item.type}
                </span>
              </div>
              <p className="mt-2 text-sm text-white/60">{item.content_preview || item.visibility}</p>
            </div>
          ))}
        </div>
      </GlassCard>
    </section>
  );
}
