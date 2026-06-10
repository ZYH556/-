"use client";

import type { ReactNode } from "react";
import { GlassButton } from "./GlassButton";
import { cx } from "./types";

interface GlassModalProps {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
  action?: ReactNode;
  className?: string;
  contained?: boolean;
}

export function GlassModal({
  open,
  title,
  children,
  onClose,
  action,
  className,
  contained = false,
}: GlassModalProps) {
  if (!open) return null;

  return (
    <div
      className={cx(
        "inset-0 z-50 grid place-items-center bg-slate-950/62 p-4",
        contained ? "absolute rounded-glass-panel" : "fixed",
      )}
    >
      <div
        className="absolute inset-0"
        aria-hidden="true"
        onClick={onClose}
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="glass-modal-title"
        className={cx(
          "glass-strong relative w-full max-w-lg rounded-glass-panel p-5",
          "shadow-glow-cyan",
          className,
        )}
      >
        <header className="mb-4 flex items-start justify-between gap-3">
          <h2 id="glass-modal-title" className="text-lg font-semibold text-white">
            {title}
          </h2>
          <GlassButton variant="ghost" onClick={onClose} aria-label="关闭弹层">
            ×
          </GlassButton>
        </header>
        <div className="text-sm leading-6 text-slate-200/88">{children}</div>
        {action && <footer className="mt-5 flex justify-end gap-2">{action}</footer>}
      </section>
    </div>
  );
}
