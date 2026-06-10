"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "./types";

type GlassButtonVariant = "primary" | "secondary" | "ghost";

interface GlassButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: GlassButtonVariant;
  active?: boolean;
  href?: string;
}

const variantClass: Record<GlassButtonVariant, string> = {
  primary: "border-cyan-200/36 bg-cyan-300/22 text-white shadow-glow-cyan",
  secondary: "border-white/16 bg-white/10 text-slate-100 hover:bg-white/16",
  ghost: "border-transparent bg-transparent text-slate-300 hover:bg-white/10",
};

export function GlassButton({
  children,
  className,
  variant = "secondary",
  active = false,
  href,
  type = "button",
  ...props
}: GlassButtonProps) {
  const classNames = cx(
    "inline-flex min-h-10 items-center justify-center rounded-glass-control",
    "border px-4 py-2 text-sm font-medium transition-glass",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-200/60",
    "disabled:cursor-not-allowed disabled:opacity-45",
    variantClass[variant],
    active && "bg-white/18 text-white",
    className,
  );

  if (href) {
    return (
      <a href={href} className={classNames}>
        {children}
      </a>
    );
  }

  return (
    <button
      type={type}
      className={classNames}
      {...props}
    >
      {children}
    </button>
  );
}
