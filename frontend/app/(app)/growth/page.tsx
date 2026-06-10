"use client";

import { useEffect, useState } from "react";

import { GlassButton, GlassCard } from "@/components/glass";
import { apiJson, getErrorMessage } from "@/lib/apiClient";
import { useAuthSession } from "@/lib/authContext";
import type { CollaborationTraceEvent, LoraExportRecord, LoraExportResult } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000/api";

export default function GrowthPage() {
  const { auth } = useAuthSession();
  const [items, setItems] = useState<CollaborationTraceEvent[]>([]);
  const [exports, setExports] = useState<LoraExportRecord[]>([]);
  const [latest, setLatest] = useState<LoraExportResult | null>(null);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiJson<{ items: CollaborationTraceEvent[] }>(
        `${API_BASE}/collaboration/traces`,
        auth.access_token,
      ),
      apiJson<{ items: LoraExportRecord[] }>(
        `${API_BASE}/growth/lora-samples`,
        auth.access_token,
      ),
    ])
      .then(([traceData, exportData]) => {
        setItems(traceData.items);
        setExports(exportData.items);
      })
      .catch((e: unknown) => setError(getErrorMessage(e)));
  }, [auth.access_token]);

  const exportSamples = async () => {
    setExporting(true);
    setError("");
    try {
      const result = await apiJson<LoraExportResult>(
        `${API_BASE}/growth/lora-samples/export`,
        auth.access_token,
        { method: "POST", body: "{}" },
      );
      setLatest(result);
      setExports((prev) => [
        {
          file_path: result.file_path,
          sample_count: result.sample_count,
          created_at: Date.now() / 1000,
          sanitized: result.sanitized,
        },
        ...prev.filter((item) => item.file_path !== result.file_path),
      ]);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold text-white">成长档案</h1>
      <GlassCard tone="mint" eyebrow="wave 2" title="LoRA 样本导出">
        {error ? <p className="text-sm text-rose-200">{error}</p> : null}
        <div className="mt-3 grid gap-3 text-sm text-white/70 md:grid-cols-3">
          <div className="rounded-2xl bg-white/10 p-3">
            <div className="text-xs text-white/45">最近样本数</div>
            <div className="mt-1 text-2xl font-semibold text-white">
              {latest?.sample_count ?? exports[0]?.sample_count ?? 0}
            </div>
          </div>
          <div className="rounded-2xl bg-white/10 p-3">
            <div className="text-xs text-white/45">过滤轨迹</div>
            <div className="mt-1 text-2xl font-semibold text-white">
              {latest?.filtered_count ?? 0}
            </div>
          </div>
          <div className="rounded-2xl bg-white/10 p-3">
            <div className="text-xs text-white/45">脱敏状态</div>
            <div className="mt-1 text-lg font-semibold text-white">
              {(latest?.sanitized ?? exports[0]?.sanitized) ? "已脱敏" : "暂无导出"}
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <GlassButton variant="primary" onClick={exportSamples} disabled={exporting}>
            {exporting ? "导出中" : "导出样本"}
          </GlassButton>
          <span className="max-w-full break-all text-xs text-white/50">
            {latest?.file_path ?? exports[0]?.file_path ?? "暂无导出文件"}
          </span>
        </div>
      </GlassCard>
      <GlassCard tone="aurora" eyebrow="wave 2" title="协作轨迹">
        <div className="mt-3 space-y-2 text-sm text-white/70">
          {items.length === 0 ? <p>暂无轨迹。完成一次对话后，这里会显示 Agent 节点事件。</p> : null}
          {items.map((item) => (
            <div key={item.trace_id} className="rounded-2xl bg-white/10 p-3">
              <div className="flex items-center justify-between gap-3 text-white">
                <span>{item.node}</span>
                <span className="text-xs text-white/50">
                  {new Date(item.created_at * 1000).toLocaleString()}
                </span>
              </div>
              <pre className="mt-2 overflow-auto text-xs text-white/60">
                {JSON.stringify(item.payload, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      </GlassCard>
    </section>
  );
}
