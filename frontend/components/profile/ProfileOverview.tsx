"use client";

import { Tag } from "@/components/workspace";
import { DossierStat, ProgressRing } from "@/components/profile/ProfileGauges";
import type { ProfileSummary } from "@/lib/types";

interface ProfileOverviewProps {
  profile: ProfileSummary;
}

const SOURCE_META: Record<string, { label: string; className: string }> = {
  redis: { label: "实时记忆", className: "text-[var(--ws-accent)]" },
  pg: { label: "历史画像", className: "text-slate-500" },
  empty: { label: "待完善", className: "text-amber-600" },
};

export function ProfileOverview({ profile }: ProfileOverviewProps) {
  const progress = Math.round(profile.progress * 100);
  const stamp = SOURCE_META[profile.source] ?? SOURCE_META.empty;
  const dossierNo = (profile.user_id || "guest").slice(0, 8).toUpperCase();

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)]">
      <section className="ws-card ws-rise p-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <span className={`ws-stamp ${stamp.className}`}>{stamp.label}</span>
          <div className="text-right">
            <p className="ws-eyebrow">Profile Nº</p>
            <p className="ws-serif mt-0.5 text-lg tracking-[0.18em] text-[var(--ws-ink)]">
              {dossierNo}
            </p>
          </div>
        </header>

        {profile.degraded.length > 0 ? (
          <div className="mt-4">
            <Tag tone="warning">部分记录同步中</Tag>
          </div>
        ) : null}

        <p className="ws-serif mt-6 text-3xl leading-tight text-[var(--ws-ink)]">
          {profile.goal || "先和 AI 学习导师聊一次，建立你的第一个学习目标。"}
        </p>

        <div className="mt-6 grid items-end gap-6 sm:grid-cols-[1fr_auto]">
          <p className="max-w-xl border-t border-dashed border-[var(--ws-line-strong)] pt-4 text-sm leading-6 text-slate-600">
            这份档案记录系统对你的当前理解：目标、基础、薄弱点与偏好。
            它直接决定 Today 的主任务、路径顺序和资源推荐——画像变了，推荐就会跟着变。
          </p>
          <ProgressRing percent={progress} />
        </div>
      </section>

      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
        <div className="ws-rise" style={{ animationDelay: "90ms" }}>
          <DossierStat
            label="学习空间"
            value={profile.spaces_count}
            hint="围绕目标沉淀的路径和资源"
          />
        </div>
        <div className="ws-rise" style={{ animationDelay: "170ms" }}>
          <DossierStat
            label="学习资源"
            value={profile.resources_count}
            hint="视频、文档、练习和个人资料"
          />
        </div>
        <div className="ws-rise" style={{ animationDelay: "250ms" }}>
          <DossierStat
            label="待复盘错题"
            value={profile.mistake_stats.open}
            hint="影响薄弱点和补救路径"
          />
        </div>
      </div>
    </div>
  );
}
