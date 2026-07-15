import Link from "next/link";
import { ArrowRight, BookOpenCheck, Clock, Star } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { OneSentenceVideoPush } from "@/components/learning-demo/OneSentenceVideoPush";
import { RoleMatrix } from "@/components/learning-demo/RoleMatrix";
import { PageHeader, Tag, WsCard } from "@/components/workspace";
import { activeCourse, courseCategories, demoCourses, featureGaps } from "@/lib/learningDemo";

export default function CoursesPage() {
  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="Courses"
        title="精品课程"
        description={`围绕《${activeCourse.course}》组织课程、视频、题库和 Agent 推荐，所有资源都回到同一门课的学习闭环。`}
      />

      <AgentProcessPanel page="courses" />
      <OneSentenceVideoPush />

      <section className="grid gap-4 md:grid-cols-3">
        {featureGaps.map((gap) => {
          const Icon = gap.icon;
          return (
            <article key={gap.label} className="ws-card p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-50 text-cyan-800">
                  <Icon size={18} aria-hidden />
                </span>
                <div>
                  <h3 className="font-medium text-[var(--ws-ink)]">{gap.label}</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{gap.note}</p>
                </div>
              </div>
            </article>
          );
        })}
      </section>

      <RoleMatrix />

      <WsCard eyebrow="Subject" title="学科分类">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {courseCategories.map((category) => {
            const Icon = category.icon;
            return (
              <article
                key={category.id}
                className="border border-[var(--ws-line)] bg-[#fbfaf7] p-4"
              >
                <Icon size={20} className="text-[var(--ws-accent)]" aria-hidden />
                <h3 className="mt-3 font-medium text-[var(--ws-ink)]">{category.title}</h3>
                <p className="mt-1 text-xs text-slate-500">{category.count} 门课程</p>
              </article>
            );
          })}
        </div>
      </WsCard>

      <section className="space-y-4">
        <div>
          <p className="ws-eyebrow">Recommended</p>
          <h2 className="ws-serif mt-1 text-2xl text-[var(--ws-ink)]">薄弱点视频推荐</h2>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {demoCourses.map((course) => (
            <article key={course.id} className="ws-card flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <Tag tone={course.level === "基础" ? "success" : "accent"}>{course.level}</Tag>
                <span className="inline-flex items-center gap-1 text-xs text-slate-500">
                  <Star size={13} aria-hidden />
                  {course.rating}
                </span>
              </div>
              <h3 className="mt-4 min-h-12 text-base font-semibold leading-6 text-[var(--ws-ink)]">
                {course.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{course.reason}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Tag tone="neutral">{course.course}</Tag>
                <Tag tone="warning">{course.weakPoint}</Tag>
                <Tag tone="neutral">
                  <Clock size={12} className="mr-1" aria-hidden />
                  {course.minutes} 分钟
                </Tag>
              </div>
              <Link
                href={`/courses/${course.id}`}
                className="mt-5 inline-flex min-h-10 items-center justify-center gap-1.5 rounded-xl border border-[var(--ws-line-strong)] bg-white px-3.5 py-2 text-sm font-medium text-[var(--ws-ink)] transition-colors hover:border-[var(--ws-navy)]"
              >
                <BookOpenCheck size={15} aria-hidden />
                进入课程
                <ArrowRight size={15} aria-hidden />
              </Link>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}
