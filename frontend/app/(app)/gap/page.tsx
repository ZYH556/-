import Link from "next/link";
import { ArrowRight, CheckCircle2, CircleAlert } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { PageHeader, Tag, WsCard } from "@/components/workspace";
import { industryCapabilities } from "@/lib/learningDemo";

export default function GapPage() {
  const advantages = industryCapabilities.filter((item) => item.status === "advantage").length;
  const improving = industryCapabilities.filter((item) => item.current < item.target).length;
  const focus = industryCapabilities.filter((item) => item.status === "focus").length;
  const match = Math.round(
    industryCapabilities.reduce((sum, item) => sum + Math.min(item.current / item.target, 1), 0) /
      industryCapabilities.length *
      100,
  );

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="Gap Report"
        title="AI 差距分析报告"
        description="基于学习画像与行业标准能力画像的智能对比分析，明确优势能力、待提升项和下一步资源建议。"
      />

      <AgentProcessPanel page="gap" />

      <section className="ws-card overflow-hidden p-0">
        <div className="bg-[linear-gradient(135deg,#0e7490,#4f46e5)] p-8 text-white">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div>
              <p className="text-sm uppercase tracking-[0.18em] text-white/70">Match Score</p>
              <h2 className="mt-2 text-5xl font-semibold">{match}%</h2>
            </div>
            <div className="max-w-2xl">
              <h3 className="text-xl font-semibold">您与行业标准的差距分析</h3>
              <p className="mt-2 text-sm leading-6 text-white/80">
                当前整体能力已接近 AI Agent 开发工程师岗位要求，但在 Agent 智能体开发、
                算法与数据结构方面仍存在明显短板，需要重点加强。
              </p>
            </div>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Metric label="优势能力" value={advantages} />
            <Metric label="待提升" value={improving} />
            <Metric label="需重点关注" value={focus} />
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <div>
          <p className="ws-eyebrow">Details</p>
          <h2 className="ws-serif mt-1 text-2xl text-[var(--ws-ink)]">能力维度差距详情</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {industryCapabilities.map((item) => {
            const diff = Math.max(item.target - item.current, 0);
            const Icon = item.status === "focus" ? CircleAlert : CheckCircle2;
            return (
              <article
                key={item.title}
                className={`ws-card border-l-4 p-5 ${
                  item.status === "focus"
                    ? "border-l-rose-400"
                    : item.status === "advantage"
                      ? "border-l-emerald-400"
                      : "border-l-slate-300"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <Icon
                    size={18}
                    className={item.status === "focus" ? "text-rose-600" : "text-emerald-700"}
                    aria-hidden
                  />
                  <Tag tone={item.status === "focus" ? "danger" : item.status === "advantage" ? "success" : "neutral"}>
                    {item.status === "focus" ? "需关注" : item.status === "advantage" ? "优势" : "达标"}
                  </Tag>
                </div>
                <h3 className="mt-3 font-medium text-[var(--ws-ink)]">{item.title}</h3>
                <div className="mt-4 flex justify-between text-xs text-slate-500">
                  <span>您：{item.current}%</span>
                  <span>目标：{item.target}%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                  <div className="h-full rounded-full bg-[var(--ws-accent)]" style={{ width: `${item.current}%` }} />
                </div>
                <p className="mt-3 text-sm font-medium text-rose-600">差距：{diff}%</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.advice}</p>
              </article>
            );
          })}
        </div>
      </section>

      <WsCard eyebrow="Next" title="AI 个性化学习建议">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="max-w-2xl text-sm leading-6 text-slate-600">
            下一步建议先完成“Vue 3 组件通信与 Pinia 状态管理”短视频，再进入 RAG 与 Agent 工作流实战。
          </p>
          <Link
            href="/courses"
            className="inline-flex min-h-10 items-center gap-1.5 rounded-xl bg-[var(--ws-navy)] px-3.5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            查看推荐课程
            <ArrowRight size={15} aria-hidden />
          </Link>
        </div>
      </WsCard>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-white/12 px-4 py-3 text-center">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-white/70">{label}</p>
    </div>
  );
}
