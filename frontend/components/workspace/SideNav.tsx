"use client";

import Link from "next/link";
import {
  BookMarked,
  Bot,
  BrainCircuit,
  ChartNoAxesColumnIncreasing,
  LayoutGrid,
  Library,
  LogOut,
  MessageSquareText,
  NotebookPen,
  PlayCircle,
  Route,
  Sprout,
  Sunrise,
  UserRoundCheck,
  type LucideIcon,
} from "lucide-react";

import { NeuronMark } from "@/app/_components/BrandMark";
import { workspaceNavItems } from "@/lib/nav";
import type { CurrentUser } from "@/lib/types";

const NAV_ICONS: Record<string, LucideIcon> = {
  today: Sunrise,
  profile: BrainCircuit,
  industry: ChartNoAxesColumnIncreasing,
  gap: ChartNoAxesColumnIncreasing,
  coach: Bot,
  mentors: UserRoundCheck,
  courses: PlayCircle,
  spaces: LayoutGrid,
  chat: MessageSquareText,
  plan: Route,
  resources: Library,
  knowledge: BookMarked,
  mistakes: NotebookPen,
  growth: Sprout,
};

const SHORT_LABELS: Record<string, string> = {
  today: "今日",
  profile: "画像",
  industry: "行业",
  gap: "差距",
  coach: "辅导",
  mentors: "匹配",
  courses: "课程",
  spaces: "目标",
  chat: "导师",
  plan: "路径",
  resources: "资源",
  knowledge: "知识",
  mistakes: "错题",
  growth: "成长",
};

interface SideNavProps {
  pathname: string;
  user: CurrentUser;
  onLogout: () => void;
}

export function SideNav({ pathname, user, onLogout }: SideNavProps) {
  return (
    <>
      <aside className="hidden shrink-0 border-r border-[var(--ws-line)] bg-white/90 text-[var(--ws-ink)] backdrop-blur lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-[72px] lg:flex-col">
        <div className="flex h-16 items-center justify-center">
          <Link
            href="/today"
            className="flex h-11 w-11 items-center justify-center transition-opacity hover:opacity-85"
            title="ReflexLearn"
          >
            <NeuronMark size={40} />
            <span className="sr-only">ReflexLearn</span>
          </Link>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-2 pb-4">
          {workspaceNavItems.map((item) => {
            const Icon = NAV_ICONS[item.id] ?? LayoutGrid;
            const active = pathname === item.href;
            return (
              <Link
                key={item.id}
                href={item.href}
                aria-current={active ? "page" : undefined}
                title={`${item.label}：${item.description}`}
                className={`flex min-h-14 flex-col items-center justify-center gap-1 text-[11px] transition-colors ${
                  active
                    ? "bg-[#eef7f8] text-[var(--ws-navy)]"
                    : "text-slate-500 hover:bg-[#f3f0e9] hover:text-[var(--ws-ink)]"
                }`}
              >
                <Icon size={18} aria-hidden />
                <span>{SHORT_LABELS[item.id] ?? item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-[var(--ws-line)] px-2 py-3">
          <button
            onClick={onLogout}
            aria-label={`退出登录：${user.user_id}`}
            title={`退出登录：${user.user_id}`}
            className="flex h-11 w-full items-center justify-center text-slate-500 transition-colors hover:bg-[#f3f0e9] hover:text-rose-700"
          >
            <LogOut size={17} aria-hidden />
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-20 border-b border-[var(--ws-line)] bg-white/90 text-[var(--ws-ink)] backdrop-blur lg:hidden">
        <div className="flex items-center justify-between px-4 pt-3">
          <Link href="/today" className="ws-serif text-lg text-[var(--ws-ink)]">
            ReflexLearn
          </Link>
          <button
            onClick={onLogout}
            aria-label={`退出登录：${user.user_id}`}
            className="p-2 text-slate-500 transition-colors hover:bg-[#f3f0e9] hover:text-rose-700"
          >
            <LogOut size={16} aria-hidden />
          </button>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-4 pb-2 pt-2">
          {workspaceNavItems.map((item) => {
            const Icon = NAV_ICONS[item.id] ?? LayoutGrid;
            const active = pathname === item.href;
            return (
              <Link
                key={item.id}
                href={item.href}
                aria-current={active ? "page" : undefined}
                title={item.description}
                className={`inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap px-2.5 py-1.5 text-xs transition-colors ${
                  active
                    ? "bg-[#eef7f8] font-medium text-[var(--ws-navy)]"
                    : "text-slate-500 hover:bg-[#f3f0e9] hover:text-[var(--ws-ink)]"
                }`}
              >
                <Icon size={14} aria-hidden />
                {SHORT_LABELS[item.id] ?? item.label}
              </Link>
            );
          })}
        </nav>
      </header>
    </>
  );
}
