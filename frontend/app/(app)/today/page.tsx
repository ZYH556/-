"use client";

import { useEffect, useState } from "react";

import { useAuthSession } from "@/lib/authContext";
import { fallbackToday } from "@/lib/todayFallback";
import { getTodaySummary } from "@/lib/todayApi";
import type { TodaySummaryView } from "@/lib/types";
import { TodayHero } from "@/components/today/TodayHero";
import { TodayMainTask } from "@/components/today/TodayMainTask";
import { LearningPathPreview } from "@/components/today/LearningPathPreview";
import { RecommendedResources } from "@/components/today/RecommendedResources";
import { TutorPrompt } from "@/components/today/TutorPrompt";
import { QuickActions } from "@/components/today/QuickActions";
import { ProfileSignals, ReviewQueue } from "@/components/today/LearningSignals";

const taskSecondaryActions = [
  { label: "让 AI 导师解释", href: "/chat", icon: "explain" },
  { label: "调整学习顺序", href: "/plan", icon: "adjust" },
] as const;

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

export default function TodayPage() {
  const { auth } = useAuthSession();
  const [remoteToday, setRemoteToday] = useState<TodaySummaryView | null>(null);
  const [loadError, setLoadError] = useState("");
  const today = remoteToday ?? fallbackToday;
  const primaryHref = today.mainTask.spaceId ? `/spaces/${today.mainTask.spaceId}` : "/spaces";

  useEffect(() => {
    let cancelled = false;
    setLoadError("");
    getTodaySummary(auth.access_token)
      .then((data) => {
        if (!cancelled) setRemoteToday(data);
      })
      .catch(() => {
        if (!cancelled) {
          setRemoteToday(null);
          setLoadError("当前显示离线学习建议，稍后会自动恢复同步。");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [auth.access_token]);

  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <TodayHero
        greeting={`${greeting()}，${today.greeting}`}
        learner={auth.user.user_id}
        goal={today.currentGoal}
        summary={`当前主线：${today.mainTask.pathNode || today.mainTask.title}`}
        progress={today.progress}
      />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1.52fr)_minmax(300px,0.78fr)]">
        <div className="space-y-8">
          <TodayMainTask
            task={today.mainTask}
            primaryHref={primaryHref}
            secondaryActions={taskSecondaryActions}
          />
          <LearningPathPreview
            phase={today.mainTask.spaceName || "学习主线"}
            progress={Math.round(today.progress * 100)}
            nodes={today.pathNodes}
            recommendation={today.pathRecommendation}
          />
          <RecommendedResources resources={today.resources} />
        </div>

        <aside className="space-y-6">
          <TutorPrompt
            prompt={{
              message: today.tutorPrompt,
              actionLabel: "和 AI 导师聊聊",
              href: "/chat",
            }}
          />
          <QuickActions actions={today.quickActions} />
          <ProfileSignals signals={today.profileSignals} />
          <ReviewQueue items={today.reviewQueue} />
        </aside>
      </div>

      {loadError ? (
        <p className="text-xs leading-5 text-slate-500" role="status">
          {loadError}
        </p>
      ) : null}
    </section>
  );
}
