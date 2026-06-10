import type { HTMLAttributes, ReactNode } from "react";
import { cx, toneClass, type GlassBaseProps } from "./types";

type GlassCardProps = GlassBaseProps &
  Omit<HTMLAttributes<HTMLElement>, "children" | "className"> & {
  eyebrow?: string;
  title?: string;
  action?: ReactNode;
};

export function GlassCard({
  children,
  className,
  tone = "default",
  eyebrow,
  title,
  action,
  ...props
}: GlassCardProps) {
  return (
    <article
      className={cx(
        "glass rounded-glass-card p-4 transition-glass hover:-translate-y-0.5",
        "hover:border-white/24 hover:shadow-glow-cyan",
        toneClass[tone],
        className,
      )}
      {...props}
    >
      {(eyebrow || title || action) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {eyebrow && (
              <p className="text-xs font-medium uppercase text-cyan-200/80">
                {eyebrow}
              </p>
            )}
            {title && (
              <h3 className="mt-1 text-base font-semibold text-white">{title}</h3>
            )}
          </div>
          {action}
        </header>
      )}
      <div className="text-sm leading-6 text-slate-200/86">{children}</div>
    </article>
  );
}
