import type { ButtonHTMLAttributes } from "react";

const VARIANTS = {
  primary:
    "bg-[var(--ws-navy)] text-white shadow-[0_1px_2px_rgb(5_26_36/0.2)] hover:opacity-90",
  outline:
    "border border-[var(--ws-line-strong)] bg-white text-[var(--ws-ink)] hover:border-[var(--ws-navy)]",
  ghost: "text-slate-600 hover:bg-[rgb(5_26_36/0.05)] hover:text-[var(--ws-ink)]",
} as const;

const SIZES = {
  sm: "px-2.5 py-1.5 text-xs",
  md: "px-3.5 py-2 text-sm",
} as const;

type WsButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
};

export function WsButton({
  variant = "outline",
  size = "md",
  className,
  type = "button",
  children,
  ...props
}: WsButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-1.5 rounded-xl font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${SIZES[size]} ${className ?? ""}`}
      {...props}
    >
      {children}
    </button>
  );
}
