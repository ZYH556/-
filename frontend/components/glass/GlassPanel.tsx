import type { HTMLAttributes } from "react";
import { cx, toneClass, type GlassBaseProps } from "./types";

type GlassPanelProps = GlassBaseProps &
  Omit<HTMLAttributes<HTMLElement>, "children" | "className"> & {
    as?: "section" | "div" | "aside";
    strong?: boolean;
  };

export function GlassPanel({
  as = "section",
  children,
  className,
  tone = "default",
  strong = false,
  ...props
}: GlassPanelProps) {
  const Component = as;

  return (
    <Component
      className={cx(
        strong ? "glass-strong" : "glass",
        toneClass[tone],
        "rounded-glass-panel p-5 shadow-glow-soft",
        className,
      )}
      {...props}
    >
      {children}
    </Component>
  );
}
