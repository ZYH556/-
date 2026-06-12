"use client";

import Link from "next/link";
import { BrandMark } from "../BrandMark";

const NAV_LINKS = [
  { label: "首页", href: "/", active: true },
  { label: "AI 辅导", href: "/chat", active: false },
  { label: "学习空间", href: "/spaces", active: false },
  { label: "学习路径", href: "/plan", active: false },
  { label: "资源生成", href: "/resources", active: false },
  { label: "成长档案", href: "/growth", active: false },
];

export function HeroHeader() {
  return (
    <header className="fixed left-0 right-0 top-0 z-40 text-foreground">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-[#001d2e]/70 via-[#001d2e]/28 to-transparent backdrop-blur-[10px] [mask-image:linear-gradient(to_bottom,black_0%,black_58%,transparent_100%)]" />
      <div className="relative mx-auto grid max-w-[1580px] grid-cols-[1fr_auto_1fr] items-center gap-4 px-6 py-5 sm:px-8">
        <div className="flex min-w-0 justify-start">
          <span className="origin-left scale-[1.04] sm:scale-[1.12]">
            <BrandMark size={34} />
          </span>
        </div>

        <nav className="hidden items-center justify-center gap-10 md:flex">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-[15px] font-medium transition-colors ${
                link.active ? "text-white" : "text-white/58 hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex justify-end">
          <Link
            href="/chat"
            className="text-sm font-medium text-white/82 transition-colors hover:text-white"
          >
            Log in
          </Link>
        </div>
      </div>
    </header>
  );
}
