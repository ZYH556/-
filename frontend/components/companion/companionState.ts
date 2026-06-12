import type { PetMood } from "./sprites";

/** 学伴产品状态：与精灵动画解耦，后续可由后台事件驱动。 */
export type CompanionStatus =
  | "idle"
  | "thinking"
  | "running"
  | "waiting"
  | "success"
  | "failed";

export const STATUS_TO_MOOD: Record<CompanionStatus, PetMood> = {
  idle: "idle",
  thinking: "think",
  running: "work",
  waiting: "study",
  success: "celebrate",
  failed: "stumble",
};

export const STATUS_LABEL: Record<CompanionStatus, string> = {
  idle: "随时可以问我",
  thinking: "正在思考",
  running: "正在执行任务",
  waiting: "等你做个选择",
  success: "建议已生成",
  failed: "服务暂时降级",
};

/** 一次性状态：播放一段后自动回到 idle。 */
export const TRANSIENT_STATUS: Partial<Record<CompanionStatus, number>> = {
  success: 2600,
  failed: 2400,
};

/** 全局状态事件名：其他模块可 dispatch 该事件驱动学伴（后台联动入口）。 */
export const COMPANION_STATUS_EVENT = "companion:status";

export interface CompanionStatusEventDetail {
  status: CompanionStatus;
  /** 可选：该状态最长保持毫秒数，超时自动回 idle。 */
  ttlMs?: number;
}

export interface PageContext {
  /** 中文页面名，展示给用户。 */
  name: string;
  /** 行为描述，进入 context_hint。 */
  activity: string;
  /** /spaces/[id] 时的空间 id。 */
  spaceId?: string;
}

const PAGE_RULES: Array<{ prefix: string; name: string; activity: string }> = [
  { prefix: "/today", name: "今日学习", activity: "用户正在查看今日学习建议" },
  { prefix: "/resources", name: "资源库", activity: "用户正在查看资源库" },
  { prefix: "/mistakes", name: "错题复盘", activity: "用户正在复盘错题" },
  { prefix: "/plan", name: "学习路径", activity: "用户正在查看学习路径" },
  { prefix: "/knowledge", name: "学习资料", activity: "用户正在管理学习资料" },
  { prefix: "/growth", name: "成长档案", activity: "用户正在查看成长档案" },
  { prefix: "/spaces", name: "学习目标", activity: "用户正在浏览学习目标" },
  { prefix: "/chat", name: "AI 导师", activity: "用户正在与 AI 导师对话" },
];

export function describePage(pathname: string): PageContext {
  const spaceMatch = /^\/spaces\/([^/]+)/.exec(pathname);
  if (spaceMatch) {
    return {
      name: "学习空间",
      activity: "用户正在查看一个学习空间的路径与资源",
      spaceId: spaceMatch[1],
    };
  }
  const hit = PAGE_RULES.find((rule) => pathname.startsWith(rule.prefix));
  if (hit) return { name: hit.name, activity: hit.activity };
  return { name: "学习系统", activity: "用户正在使用学习系统" };
}

/** 组装 /api/tutor/ask 的 context_hint：结构化字段 + 行为描述。 */
export function buildContextHint(pathname: string): string {
  const page = describePage(pathname);
  const parts = [`pathname=${pathname}`, `page=${page.name}`];
  if (page.spaceId) parts.push(`space_id=${page.spaceId}`);
  parts.push(page.activity);
  return parts.join(" | ");
}
