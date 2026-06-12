import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: LucideIcon;
}

export function StatCard({ label, value, hint, icon: Icon }: StatCardProps) {
  return (
    <div className="ws-card p-4">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        {Icon ? <Icon size={14} className="text-slate-400" aria-hidden /> : null}
        <span>{label}</span>
      </div>
      <div className="ws-serif mt-2 text-3xl text-[var(--ws-ink)]">{value}</div>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}
