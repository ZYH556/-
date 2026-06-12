import Link from "next/link";
import { ArrowRight, Clock3, MessageCircleQuestion, SlidersHorizontal } from "lucide-react";

import type { TodayTask } from "./types";

type TodayMainTaskProps = {
  task: TodayTask;
  primaryHref?: string;
  secondaryActions: readonly {
    label: string;
    href: string;
    icon: "explain" | "adjust";
  }[];
};

const ACTION_ICONS = {
  explain: MessageCircleQuestion,
  adjust: SlidersHorizontal,
} as const;

export function TodayMainTask({
  task,
  primaryHref = "/chat",
  secondaryActions,
}: TodayMainTaskProps) {
  return (
    <section className="bg-white px-5 py-6 shadow-[0_18px_50px_rgb(5_26_36/0.06)] sm:px-7 sm:py-7">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
        <span>{task.spaceName}</span>
        <span className="h-1 w-1 bg-slate-300" aria-hidden />
        <span>{task.pathNode}</span>
        <span className="inline-flex items-center gap-1.5">
          <Clock3 size={15} aria-hidden />
          {task.estimatedMinutes} 分钟
        </span>
      </div>

      <h2 className="mt-5 max-w-3xl text-2xl font-medium leading-snug text-[var(--ws-ink)] sm:text-3xl">
        {task.title}
      </h2>
      <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">{task.reason}</p>

      <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center">
        <Link
          href={primaryHref}
          className="inline-flex items-center justify-center gap-2 bg-[var(--ws-navy)] px-5 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          {task.primaryAction}
          <ArrowRight size={16} aria-hidden />
        </Link>
        {secondaryActions.map((action) => {
          const Icon = ACTION_ICONS[action.icon];
          return (
            <Link
              key={action.label}
              href={action.href}
              className="inline-flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-slate-600 transition-colors hover:bg-[rgb(5_26_36/0.05)] hover:text-[var(--ws-ink)]"
            >
              <Icon size={16} aria-hidden />
              {action.label}
            </Link>
          );
        })}
      </div>
    </section>
  );
}
