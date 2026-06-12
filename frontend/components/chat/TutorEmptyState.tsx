"use client";

import { Gauge, GraduationCap, Route } from "lucide-react";

const QUESTIONS = [
  {
    icon: GraduationCap,
    text: "你正在准备什么课程、考试或项目？",
  },
  {
    icon: Gauge,
    text: "你目前的基础如何？",
  },
  {
    icon: Route,
    text: "你希望我先帮你规划路径、解释知识点，还是生成资源？",
  },
];

export function TutorEmptyState() {
  return (
    <section className="border border-[var(--ws-line-strong)] bg-white p-5">
      <div className="max-w-2xl">
        <p className="text-sm font-medium text-[var(--ws-ink)]">
          先把学习目标讲清楚，AI 导师会根据你的基础、薄弱点和偏好给出下一步。
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {QUESTIONS.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.text} className="border-l border-[var(--ws-line-strong)] pl-3">
                <Icon size={17} className="text-[var(--ws-accent)]" aria-hidden />
                <p className="mt-2 text-sm leading-6 text-slate-600">{item.text}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
