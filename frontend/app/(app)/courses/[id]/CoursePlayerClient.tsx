"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, MessageSquareReply, Play, Send, Star, UserRound } from "lucide-react";

import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { PageHeader, Tag, WsButton, WsCard } from "@/components/workspace";
import { demoCourses } from "@/lib/learningDemo";

export function CoursePlayerClient({ id }: { id: string }) {
  const course = useMemo(
    () => demoCourses.find((item) => item.id === id) ?? demoCourses[0],
    [id],
  );
  const [question, setQuestion] = useState("Java 基础学哪些？");
  const [reply, setReply] = useState("");
  const [chapterIndex, setChapterIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [completed, setCompleted] = useState<number[]>([]);
  const currentChapter = course.chapters[chapterIndex] ?? course.chapters[0];
  const progress = Math.round((completed.length / course.chapters.length) * 100);

  const generateReply = () => {
    setReply(
      `AI 辅助助手已根据《${course.title}》的目录生成回复：先补 ${course.weakPoint}，再完成章节练习。建议你按“概念理解 -> 案例跟练 -> 错题复盘”的顺序学习，遇到概念不清时可以继续追问。`,
    );
  };

  const toggleComplete = () => {
    setCompleted((items) =>
      items.includes(chapterIndex)
        ? items.filter((item) => item !== chapterIndex)
        : [...items, chapterIndex],
    );
  };

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="Course Player"
        title={course.title}
        description="课程播放、章节目录、讨论区和 AI 智能回复放在同一页，学习行为会反哺画像与路径。"
        actions={
          <Link
            href="/courses"
            className="inline-flex items-center gap-1.5 rounded-xl border border-[var(--ws-line-strong)] bg-white px-3.5 py-2 text-sm font-medium text-[var(--ws-ink)] transition-colors hover:border-[var(--ws-navy)]"
          >
            <ArrowLeft size={15} aria-hidden />
            返回课程
          </Link>
        }
      />

      <AgentProcessPanel page="courses" title="课程页 Agent 调用过程" />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]">
        <div className="space-y-6">
          <section className="overflow-hidden rounded-2xl border border-[var(--ws-line)] bg-[#111827] text-white shadow-[0_1px_2px_rgb(5_26_36/0.08)]">
            <div className="flex aspect-video flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_center,_rgba(14,116,144,0.34),_transparent_42%),linear-gradient(135deg,#071923,#111827)]">
              <button
                type="button"
                onClick={() => setPlaying((value) => !value)}
                className="flex h-16 w-16 items-center justify-center rounded-full border border-white/20 bg-white/10 transition-transform hover:scale-105"
                aria-label={playing ? "暂停课程播放" : "播放课程"}
              >
                <Play size={28} aria-hidden />
              </button>
              <div className="text-center">
                <p className="text-sm text-white/65">{playing ? "正在播放" : "课程视频播放区域"}</p>
                <h2 className="mt-2 text-2xl font-semibold">{currentChapter.title}</h2>
                <p className="mt-2 text-sm text-white/60">{course.title}</p>
              </div>
              <div className="mt-2 w-2/3 max-w-md">
                <div className="h-1.5 overflow-hidden rounded-full bg-white/15">
                  <div
                    className="h-full rounded-full bg-cyan-300 transition-all"
                    style={{ width: playing ? "62%" : `${Math.max(progress, 8)}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-white/55">
                  <span>{playing ? "12:46" : "待播放"}</span>
                  <span>{currentChapter.duration}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-4 py-3 text-sm text-white/70">
              <span>学习进度 {progress}%</span>
              <button
                type="button"
                onClick={toggleComplete}
                className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 px-3 py-1.5 text-white transition-colors hover:bg-white/10"
              >
                <CheckCircle2 size={15} aria-hidden />
                {completed.includes(chapterIndex) ? "取消完成" : "标记本章完成"}
              </button>
            </div>
          </section>

          <WsCard eyebrow="Discussion" title="课程讨论区">
            <div className="border border-[var(--ws-line)] bg-[#fbfaf7] p-4">
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-slate-500">
                  <UserRound size={16} aria-hidden />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium text-[var(--ws-ink)]">{question}</p>
                    <Tag tone="warning">待回复</Tag>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">admin · 当前课程讨论</p>
                </div>
              </div>

              {reply ? (
                <div className="mt-4 border-l-2 border-cyan-400 bg-cyan-50 px-4 py-3 text-sm leading-6 text-slate-700">
                  <p className="mb-1 inline-flex items-center gap-1.5 font-medium text-cyan-900">
                    <MessageSquareReply size={15} aria-hidden />
                    AI 智能回复
                  </p>
                  <p>{reply}</p>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                className="min-h-11 flex-1 border border-[var(--ws-line-strong)] bg-white px-3 text-sm text-[var(--ws-ink)] outline-none focus:border-[var(--ws-navy)]"
              />
              <WsButton variant="primary" onClick={generateReply}>
                <Send size={15} aria-hidden />
                AI 回复
              </WsButton>
            </div>
          </WsCard>
        </div>

        <aside className="space-y-6">
          <WsCard title={course.title} eyebrow="Course">
            <div className="flex flex-wrap gap-2">
              <Tag tone="accent">{course.course}</Tag>
              <Tag tone="warning">{course.weakPoint}</Tag>
              <Tag tone="neutral">
                <Star size={12} className="mr-1" aria-hidden />
                {course.rating}
              </Tag>
            </div>
            <p className="mt-4 text-sm leading-6 text-slate-600">{course.reason}</p>
          </WsCard>

          <WsCard eyebrow="Chapters" title="课程目录">
            <ol className="space-y-2">
              {course.chapters.map((chapter, index) => (
                <li key={chapter.title}>
                  <button
                    type="button"
                    onClick={() => {
                      setChapterIndex(index);
                      setPlaying(true);
                    }}
                    className={`flex w-full items-center justify-between gap-3 border px-3 py-2 text-left text-sm ${
                      index === chapterIndex
                        ? "border-cyan-200 bg-cyan-50 text-cyan-950"
                        : "border-[var(--ws-line)] bg-[#fbfaf7] text-slate-600"
                    }`}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      {completed.includes(index) ? (
                        <CheckCircle2 size={14} className="shrink-0 text-emerald-700" aria-hidden />
                      ) : null}
                      <span className="truncate">{chapter.title}</span>
                    </span>
                    <span className="shrink-0 text-xs text-slate-500">{chapter.duration}</span>
                  </button>
                </li>
              ))}
            </ol>
          </WsCard>
        </aside>
      </div>
    </section>
  );
}
