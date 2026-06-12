import type { HTMLAttributes } from "react";

const TONES = {
  neutral: "border-slate-200 bg-slate-100 text-slate-700",
  navy: "border-[rgb(5_26_36/0.12)] bg-[rgb(5_26_36/0.06)] text-[var(--ws-ink)]",
  accent: "border-cyan-200 bg-cyan-50 text-cyan-800",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
} as const;

export type TagTone = keyof typeof TONES;

type TagProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: TagTone;
};

export function Tag({ tone = "neutral", className, children, ...props }: TagProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className ?? ""}`}
      {...props}
    >
      {children}
    </span>
  );
}
