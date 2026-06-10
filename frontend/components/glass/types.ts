import type { ReactNode } from "react";

export type GlassTone = "default" | "aurora" | "ember" | "mint";

export interface GlassBaseProps {
  children: ReactNode;
  className?: string;
  tone?: GlassTone;
}

export function cx(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export const toneClass: Record<GlassTone, string> = {
  default: "",
  aurora: "glass-aurora",
  ember: "glass-ember",
  mint: "glass-mint",
};
