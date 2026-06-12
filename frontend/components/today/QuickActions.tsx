import Link from "next/link";
import {
  ClipboardList,
  FileQuestion,
  Flag,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import type { QuickAction } from "./types";

const ACTION_ICONS: Record<QuickAction["icon"], LucideIcon> = {
  upload: UploadCloud,
  mistake: FileQuestion,
  practice: ClipboardList,
  goal: Flag,
};

type QuickActionsProps = {
  actions: QuickAction[];
};

export function QuickActions({ actions }: QuickActionsProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-[var(--ws-ink)]">快速动作</h2>
      <div className="grid grid-cols-2 gap-2">
        {actions.map((action) => {
          const Icon = ACTION_ICONS[action.icon];
          return (
            <Link
              key={action.id}
              href={action.href}
              className="group min-h-28 bg-white p-4 transition-colors hover:bg-[#f0eee7]"
              title={action.description}
            >
              <Icon size={18} className="text-[var(--ws-accent)]" aria-hidden />
              <p className="mt-3 text-sm font-medium leading-5 text-[var(--ws-ink)]">
                {action.label}
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500">{action.description}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
