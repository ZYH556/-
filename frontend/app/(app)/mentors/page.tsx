"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, BadgeCheck, RotateCw, UserRoundCheck } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { PageHeader, Tag, WsButton, WsCard } from "@/components/workspace";
import { activeCourse, mentorCards } from "@/lib/learningDemo";

export default function MentorsPage() {
  const [matching, setMatching] = useState(false);
  const [matched, setMatched] = useState(true);
  const [stage, setStage] = useState("画像匹配完成");

  const runMatch = () => {
    setMatching(true);
    setMatched(false);
    setStage("读取学习画像与课程目标");
    window.setTimeout(() => setStage("计算薄弱点与导师能力匹配"), 320);
    window.setTimeout(() => setStage("生成辅导入口与推荐排序"), 640);
    window.setTimeout(() => {
      setMatching(false);
      setMatched(true);
      setStage("画像匹配完成");
    }, 900);
  };

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="Mentor Match"
        title="AI 导师智能匹配"
        description="基于学习风格、薄弱知识点、目标课程和职业方向，通过多维加权算法精准匹配最适合的辅导老师。"
        actions={
          <WsButton variant="primary" onClick={runMatch} disabled={matching}>
            <RotateCw size={15} aria-hidden />
            {matching ? "匹配中…" : "重新匹配"}
          </WsButton>
        }
      />

      <AgentProcessPanel page="mentors" />

      <WsCard eyebrow="Profile" title="匹配条件">
        <div className="grid gap-3 md:grid-cols-4">
          <Field label="目标学生" value={`${activeCourse.subject} · ${activeCourse.grade}`} />
          <Field label="课程方向" value={activeCourse.course} />
          <Field label="目标岗位" value={activeCourse.target} />
          <Field label="匹配人数" value="3 位" />
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {["学习风格 30%", "薄弱知识点 45%", "岗位目标 25%"].map((item) => (
            <div key={item} className="border border-[var(--ws-line)] bg-[#fbfaf7] px-3 py-2 text-xs text-slate-600">
              {item}
            </div>
          ))}
        </div>
      </WsCard>

      <div className="text-center">
        <p className="ws-eyebrow">Result</p>
        <h2 className="ws-serif mt-1 text-2xl text-[var(--ws-ink)]">
          {matched ? "为您匹配到 3 位导师" : "正在计算导师匹配度"}
        </h2>
        <p className="mt-2 text-sm text-slate-500">{stage}</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {mentorCards.map((mentor, index) => (
          <article key={mentor.name} className="ws-card p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#f0eee7] text-[var(--ws-accent)]">
                  <UserRoundCheck size={18} aria-hidden />
                </span>
                <div className="min-w-0">
                  <h3 className="truncate font-semibold text-[var(--ws-ink)]">{mentor.name}</h3>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{mentor.title}</p>
                </div>
              </div>
              <Tag tone={index === 0 ? "accent" : "neutral"}>
                {index === 0 ? "最佳匹配" : `第 ${index + 1} 推荐`}
              </Tag>
            </div>

            <div className="mt-5">
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>匹配度</span>
                <span className="font-medium text-[var(--ws-ink)]">
                  {matching ? "--" : `${mentor.match}%`}
                </span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-[var(--ws-accent)]"
                  style={{ width: matching ? "0%" : `${mentor.match}%` }}
                />
              </div>
            </div>

            <p className="mt-4 text-sm leading-6 text-slate-600">{mentor.reason}</p>

            <div className="mt-4 space-y-2">
              {mentor.strengths.map((item) => (
                <p key={item} className="flex items-center gap-2 text-xs text-slate-600">
                  <BadgeCheck size={14} className="text-emerald-700" aria-hidden />
                  {item}
                </p>
              ))}
            </div>
            <Link
              href="/coach"
              className="mt-5 inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-[var(--ws-line-strong)] bg-white px-3.5 py-2 text-sm font-medium text-[var(--ws-ink)] transition-colors hover:border-[var(--ws-navy)]"
            >
              进入辅导
              <ArrowRight size={15} aria-hidden />
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[var(--ws-line)] bg-[#fbfaf7] px-4 py-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-[var(--ws-ink)]">{value}</p>
    </div>
  );
}
