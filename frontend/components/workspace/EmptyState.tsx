import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-[var(--ws-line-strong)] bg-white/60 px-6 py-12 text-center">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[rgb(5_26_36/0.05)] text-slate-500">
        <Icon size={20} aria-hidden />
      </span>
      <h3 className="mt-4 font-medium text-[var(--ws-ink)]">{title}</h3>
      {description ? (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-slate-600">
          {description}
        </p>
      ) : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
