"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Loader2, Send, Sparkles } from "lucide-react";

import { demoCourses, oneSentenceAgentSteps, recommendedVideo } from "@/lib/learningDemo";
import { Tag, WsButton, WsCard } from "@/components/workspace";

const defaultCommand = "给我推送一个适合当前薄弱点的短视频";

export function OneSentenceVideoPush({
  compact = false,
}: {
  compact?: boolean;
}) {
  const [command, setCommand] = useState(defaultCommand);
  const [generated, setGenerated] = useState(compact);
  const [running, setRunning] = useState(false);
  const [activeStep, setActiveStep] = useState(compact ? oneSentenceAgentSteps.length : 0);
  const VideoIcon = recommendedVideo.icon;
  const course = demoCourses[1];

  const execute = () => {
    if (!command.trim() || running) return;
    setRunning(true);
    setGenerated(false);
    setActiveStep(0);

    oneSentenceAgentSteps.forEach((_, index) => {
      window.setTimeout(() => setActiveStep(index + 1), 320 * (index + 1));
    });
    window.setTimeout(() => {
      setGenerated(true);
      setRunning(false);
    }, 320 * (oneSentenceAgentSteps.length + 1));
  };

  return (
    <WsCard
      eyebrow="One Sentence"
      title="一句话学习动作"
      action={<Tag tone={generated ? "success" : running ? "accent" : "neutral"}>{generated ? "已推送" : running ? "调用中" : "待执行"}</Tag>}
    >
      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="sr-only" htmlFor="one-sentence-command">
          一句话学习动作
        </label>
        <input
          id="one-sentence-command"
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          className="min-h-11 flex-1 border border-[var(--ws-line-strong)] bg-white px-3 text-sm text-[var(--ws-ink)] outline-none transition-colors focus:border-[var(--ws-navy)]"
          placeholder={defaultCommand}
        />
        <WsButton
          variant="primary"
          onClick={execute}
          disabled={!command.trim() || running}
          className="min-h-11"
        >
          {running ? <Loader2 size={15} className="animate-spin" aria-hidden /> : <Send size={15} aria-hidden />}
          {running ? "执行中" : "执行"}
        </WsButton>
      </div>

      {(running || generated) ? (
        <div className="mt-4 grid gap-2 md:grid-cols-3">
          {oneSentenceAgentSteps.map((step, index) => {
            const done = index < activeStep;
            const current = running && index === activeStep;
            return (
              <div
                key={step.label}
                className={`border px-3 py-2 text-xs ${
                  done
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : current
                      ? "border-cyan-200 bg-cyan-50 text-cyan-900"
                      : "border-[var(--ws-line)] bg-[#fbfaf7] text-slate-500"
                }`}
              >
                <p className="flex items-center gap-1.5 font-medium">
                  {done ? <CheckCircle2 size={13} aria-hidden /> : <Sparkles size={13} aria-hidden />}
                  {step.label}
                </p>
                <p className="mt-1 leading-5">{step.detail}</p>
              </div>
            );
          })}
        </div>
      ) : null}

      {generated ? (
        <article className="mt-5 border border-cyan-200 bg-cyan-50 p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white text-cyan-800">
                <VideoIcon size={20} aria-hidden />
              </span>
              <div>
                <Tag tone="accent">{recommendedVideo.action}</Tag>
                <h3 className="mt-2 font-medium text-[var(--ws-ink)]">
                  {recommendedVideo.title}
                </h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">
                  {recommendedVideo.source}
                </p>
                <p className="mt-2 inline-flex items-center gap-1.5 text-xs text-slate-500">
                  <Sparkles size={13} aria-hidden />
                  视频 Agent 已关联课程：{course.course} · {recommendedVideo.duration}
                </p>
              </div>
            </div>
            <Link
              href={`/courses/${course.id}`}
              className="inline-flex min-h-10 items-center gap-1.5 rounded-xl bg-[var(--ws-navy)] px-3.5 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              去学习
              <ArrowRight size={15} aria-hidden />
            </Link>
          </div>
        </article>
      ) : null}
    </WsCard>
  );
}
