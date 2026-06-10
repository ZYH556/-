"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiJson, authFetch, getErrorMessage } from "@/lib/apiClient";
import type { VideoJob } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

type Status = "idle" | "submitting" | "polling" | "settled" | "error";

interface VideoJobCardProps {
  token: string;
}

const STATUS_LABEL: Record<string, string> = {
  pending: "排队中",
  running: "生成中",
  done: "完成",
  degraded: "降级（展示分镜脚本）",
  failed: "失败",
};

const STATUS_BADGE: Record<string, string> = {
  done: "bg-emerald-500",
  degraded: "bg-amber-500",
  failed: "bg-rose-500",
};

/** M4-F 多模态视频作业：提交 storyboard → POST /api/video/jobs → 2s 轮询 GET 直到 settled。 */
export function VideoJobCard({ token }: VideoJobCardProps) {
  const [storyboard, setStoryboard] = useState("");
  const [job, setJob] = useState<VideoJob | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 卸载时清掉未完成的轮询定时器
  useEffect(() => () => {
    if (pollRef.current) clearTimeout(pollRef.current);
  }, []);

  const poll = useCallback((jobId: string) => {
    let tries = 0;
    const tick = async () => {
      tries += 1;
      try {
        const r = await authFetch(`${API_BASE}/video/jobs/${jobId}`, token);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const j: VideoJob = await r.json();
        setJob(j);
        if (["done", "degraded", "failed"].includes(j.status) || tries > 30) {
          setStatus("settled");
          return;
        }
      } catch (e: unknown) {
        setError(getErrorMessage(e));
        setStatus("error");
        return;
      }
      pollRef.current = setTimeout(tick, 2000);
    };
    tick();
  }, [token]);

  const submit = useCallback(async () => {
    if (!storyboard.trim()) return;
    setStatus("submitting");
    setError("");
    setJob(null);
    try {
      const data = await apiJson<{ job_id: string; status: string }>(
        `${API_BASE}/video/jobs`,
        token,
        {
          method: "POST",
          body: JSON.stringify({ storyboard }),
        },
      );
      setStatus("polling");
      poll(data.job_id);
    } catch (e: unknown) {
      setError(getErrorMessage(e));
      setStatus("error");
    }
  }, [storyboard, poll, token]);

  const busy = status === "submitting" || status === "polling";

  return (
    <div className="space-y-3 border-t border-slate-100 pt-4">
      <h3 className="text-sm font-semibold text-slate-700">🎬 多模态视频生成（SeeDance）</h3>
      <textarea
        value={storyboard}
        onChange={(e) => setStoryboard(e.target.value)}
        placeholder="粘贴分镜脚本（storyboard），或用对话生成「多模态视频」资源后复制其内容…"
        rows={3}
        className="w-full rounded-lg border border-slate-300 p-2 text-sm"
      />
      <button
        onClick={submit}
        disabled={!storyboard.trim() || busy}
        className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-40"
      >
        {status === "submitting" ? "提交中…" : status === "polling" ? "生成中…（轮询）" : "生成视频"}
      </button>

      {status === "error" && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {job && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium text-white ${
                STATUS_BADGE[job.status] || "bg-indigo-500"
              }`}
            >
              {STATUS_LABEL[job.status] || job.status}
            </span>
            <code className="text-xs text-slate-400">{job.job_id.slice(0, 8)}</code>
          </div>
          {job.status === "done" && job.video_url && (
            <a
              href={job.video_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-indigo-600 underline"
            >
              ▶ 查看生成的视频
            </a>
          )}
          {job.status === "degraded" && (
            <div className="mt-2">
              <div className="text-xs text-amber-600">SeeDance 未配置，展示分镜脚本占位：</div>
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-xs text-slate-600">
                {job.storyboard}
              </pre>
            </div>
          )}
          {job.status === "failed" && (
            <div className="mt-2 text-xs text-rose-600">{job.error}</div>
          )}
        </div>
      )}
    </div>
  );
}
