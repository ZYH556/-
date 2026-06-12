import type { SpacePathStep } from "@/lib/types";

export function progressPercent(progress: number): number {
  return Math.max(0, Math.min(100, Math.round((progress || 0) * 100)));
}

export function statusLabel(status: string): string {
  if (status === "active") return "进行中";
  if (status === "archived") return "已归档";
  if (status === "done" || status === "completed") return "已完成";
  return status || "待开始";
}

export function nextStep(steps: SpacePathStep[]): SpacePathStep | null {
  return (
    steps.find((step) => step.mastery_status === "in_progress") ??
    steps.find((step) => step.mastery_status !== "done") ??
    steps[0] ??
    null
  );
}

export function doneStepCount(steps: SpacePathStep[]): number {
  return steps.filter((step) => step.mastery_status === "done").length;
}
