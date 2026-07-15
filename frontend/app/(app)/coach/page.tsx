"use client";

import { useState } from "react";
import Link from "next/link";
import { BarChart3, FileQuestion, Link2, Send, TriangleAlert, Video } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { OneSentenceVideoPush } from "@/components/learning-demo/OneSentenceVideoPush";
import { PageHeader, Tag, WsButton, WsCard } from "@/components/workspace";
import { activeCourse, quickToolActions } from "@/lib/learningDemo";

const diagnosticQuestions = [
  "你在 React 基础和 Vue 基础方面最常遇到的具体困难是什么？",
  "组件通信、状态管理、生命周期中，哪些概念最容易混淆？",
  "在数据结构和算法方面，你更害怕题型理解还是代码实现？",
  "你对 Transformer 和 MySQL 的结合应用更想先补哪一块？",
  "最近错题中是否有反复出现但还说不清原因的问题？",
];

const coachResult = {
  title: "已生成一轮辅导动作",
  diagnosis: "你的描述集中在 Vue 组件通信和状态管理，系统将它归入“前端状态流转”薄弱点。",
  steps: ["先看 18 分钟短视频补概念", "完成 3 道组件通信专项练习", "把错题同步到学习路径做二次复盘"],
};

export default function CoachPage() {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="AI Coach"
        title="AI 智能辅导"
        description="像对话助手一样，用一句话触发诊断、资源生成、视频推送和错题复盘。"
      />

      <AgentProcessPanel page="coach" />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <div className="space-y-6">
          <WsCard eyebrow="Dialogue" title="辅导对话">
            <div className="border border-[var(--ws-line)] bg-[#fbfaf7] p-5">
              <div className="flex gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-200 text-slate-600">
                  AI
                </span>
                <div className="text-sm leading-7 text-slate-700">
                  <p>
                    同学，根据你的学习画像和薄弱知识点，以下是 3-5 个诊断性问题。
                    回答后我会继续为你生成学习计划和资源。
                  </p>
                  <ol className="mt-3 list-decimal space-y-1 pl-5">
                    {diagnosticQuestions.map((question) => (
                      <li key={question}>{question}</li>
                    ))}
                  </ol>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Tag tone="accent">学习画像分析</Tag>
                <Tag tone="warning">错题分析</Tag>
              </div>
            </div>

            <div className="mt-5 space-y-3">
              <label htmlFor="coach-answer" className="text-sm font-medium text-[var(--ws-ink)]">
                输入你的问题或想法
              </label>
              <textarea
                id="coach-answer"
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                className="min-h-28 w-full resize-y border border-[var(--ws-line-strong)] bg-white px-3 py-2 text-sm text-[var(--ws-ink)] outline-none focus:border-[var(--ws-navy)]"
                placeholder="例如：我想先补 Vue 的组件通信，再做一套专项练习。"
              />
              <div className="flex justify-end">
                <WsButton variant="primary" onClick={() => setSubmitted(true)} disabled={!answer.trim()}>
                  <Send size={15} aria-hidden />
                  发送
                </WsButton>
              </div>
              {submitted ? (
                <div className="border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="font-medium">{coachResult.title}</p>
                    <Tag tone="success">已同步到演示链路</Tag>
                  </div>
                  <p className="mt-2 leading-6">{coachResult.diagnosis}</p>
                  <ol className="mt-3 grid gap-2 md:grid-cols-3">
                    {coachResult.steps.map((step, index) => (
                      <li key={step} className="border border-emerald-200 bg-white/70 px-3 py-2">
                        <p className="text-xs text-emerald-700">动作 {index + 1}</p>
                        <p className="mt-1 leading-5">{step}</p>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </div>
          </WsCard>

          <OneSentenceVideoPush compact />
        </div>

        <aside className="space-y-6">
          <WsCard eyebrow="Learner" title="学习画像">
            <dl className="space-y-3 text-sm">
              <InfoRow label="专业" value={activeCourse.subject} />
              <InfoRow label="年级" value={activeCourse.grade} />
              <InfoRow label="课程" value={activeCourse.course} />
              <InfoRow label="目标方向" value={activeCourse.target} />
            </dl>
          </WsCard>

          <WsCard eyebrow="Weakness" title="薄弱环节">
            <div className="flex flex-wrap gap-2">
              {["React 基础", "fastApi", "算法", "Vue 基础", "Pinia", "MySQL", "数据结构"].map((item) => (
                <Tag key={item} tone="danger">{item}</Tag>
              ))}
            </div>
          </WsCard>

          <WsCard eyebrow="Tools" title="快速工具">
            <div className="space-y-2">
              {quickToolActions.map((item, index) => {
                const Icon = [BarChart3, FileQuestion, Link2, TriangleAlert, Video][index] ?? Link2;
                return (
                  <Link
                    key={item.label}
                    href={item.target}
                    className={`flex min-h-10 items-center justify-center gap-2 border border-[var(--ws-line)] px-3 py-2 text-sm transition-colors ${
                      index === quickToolActions.length - 1
                        ? "bg-[var(--ws-navy)] text-white hover:opacity-90"
                        : "bg-white text-slate-700 hover:border-[var(--ws-navy)]"
                    }`}
                  >
                    <Icon size={15} aria-hidden />
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </WsCard>
        </aside>
      </div>
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[var(--ws-line)] pb-2 last:border-b-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-[var(--ws-ink)]">{value}</dd>
    </div>
  );
}
