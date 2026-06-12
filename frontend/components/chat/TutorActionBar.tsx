"use client";

import {
  BookOpenCheck,
  ClipboardList,
  Library,
  ListChecks,
  RotateCcw,
  type LucideIcon,
} from "lucide-react";

export type TutorAction = {
  label: string;
  prompt: string;
  icon: LucideIcon;
};

export const TUTOR_ACTIONS: TutorAction[] = [
  {
    label: "构建学习画像",
    prompt:
      "You are a one-on-one AI learning tutor. Diagnose my learning goal, current level, weak points, and learning preferences with 3 to 5 concise questions before summarizing my learner profile.",
    icon: ClipboardList,
  },
  {
    label: "生成学习路径",
    prompt:
      "You are a one-on-one AI learning tutor. Create a staged learning path for my goal with objectives, prerequisites, practice methods, and checkpoints for each stage.",
    icon: ListChecks,
  },
  {
    label: "生成一组练习",
    prompt:
      "You are a one-on-one AI learning tutor. Generate a short practice set from easy to hard around my weakest concept, then provide self-check criteria.",
    icon: BookOpenCheck,
  },
  {
    label: "复盘一道错题",
    prompt:
      "You are a one-on-one AI learning tutor. Guide me to provide the question, my answer, and the expected answer, then analyze the error cause and propose remedial practice.",
    icon: RotateCcw,
  },
  {
    label: "推荐学习资源",
    prompt:
      "You are a one-on-one AI learning tutor. Recommend learning resources based on my goal and weak points, and explain which problem each resource helps solve.",
    icon: Library,
  },
];

export function TutorActionBar({
  disabled,
  onSelect,
}: {
  disabled: boolean;
  onSelect: (prompt: string, displayMessage?: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {TUTOR_ACTIONS.map((action) => {
        const Icon = action.icon;
        return (
          <button
            key={action.label}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(action.prompt, action.label)}
            className="inline-flex items-center gap-2 border border-[var(--ws-line-strong)] bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-[var(--ws-accent)] hover:text-[var(--ws-ink)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Icon size={15} aria-hidden />
            {action.label}
          </button>
        );
      })}
    </div>
  );
}
