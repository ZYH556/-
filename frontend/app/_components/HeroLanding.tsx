"use client";

import Link from "next/link";
import { BrandMark } from "./BrandMark";

const NAV_LINKS = [
  { label: "首页", href: "/", active: true },
  { label: "工作台", href: "/chat", active: false },
  { label: "学习空间", href: "/spaces", active: false },
  { label: "学习赛道", href: "/tracks/ai-programming", active: false },
  { label: "设计系统", href: "/design", active: false },
];

/** 能力卡线性小图标（深青描边，白色面板配色）。 */
function CapabilityIcon({ kind }: { kind: "agents" | "rag" | "path" | "flywheel" }) {
  const common = {
    width: 30,
    height: 30,
    viewBox: "0 0 32 32",
    fill: "none",
    stroke: "#0e7490",
    strokeWidth: 1.7,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (kind === "agents")
    return (
      <svg {...common}>
        <circle cx="16" cy="7" r="3" />
        <circle cx="7" cy="24" r="3" />
        <circle cx="25" cy="24" r="3" />
        <path d="M14 9.5 8.5 21.5M18 9.5 23.5 21.5M10 24h12" />
      </svg>
    );
  if (kind === "rag")
    return (
      <svg {...common}>
        <path d="M4 8c0-1.7 5.4-3 12-3s12 1.3 12 3-5.4 3-12 3S4 9.7 4 8Z" />
        <path d="M4 8v8c0 1.7 5.4 3 12 3s12-1.3 12-3V8" />
        <path d="M4 16v8c0 1.7 5.4 3 12 3s12-1.3 12-3v-8" />
      </svg>
    );
  if (kind === "path")
    return (
      <svg {...common}>
        <circle cx="6" cy="26" r="2.6" />
        <circle cx="16" cy="16" r="2.6" />
        <circle cx="26" cy="6" r="2.6" />
        <path d="M8 24l6-6M18 14l6-6" strokeDasharray="0.1 4" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="M26 16a10 10 0 1 1-3-7.1" />
      <path d="M26 5v5h-5" />
      <circle cx="16" cy="16" r="2.4" fill="#0e7490" stroke="none" />
    </svg>
  );
}

const CAPABILITIES = [
  {
    kind: "agents" as const,
    title: "多智能体协作",
    desc: "画像、规划、生成、批判、辩论、裁决——六个角色围绕你的目标实时协作，每一步都在工作台中可见。",
  },
  {
    kind: "rag" as const,
    title: "混合检索增强",
    desc: "语义向量、关键词、知识图谱三路并发召回，再经融合排序，让每一份资源的生成都有据可依。",
  },
  {
    kind: "path" as const,
    title: "个性化学习路径",
    desc: "按你的薄弱点与认知风格排出学习步骤，每一步都标注目标、难度与排序理由，先补短板、由浅入深。",
  },
  {
    kind: "flywheel" as const,
    title: "自进化飞轮",
    desc: "Reflexion 经验记忆与元认知自审在每轮协作后沉淀——你用得越多，系统越懂你。",
  },
];

const STATS = [
  { value: "6", unit: "种", label: "学习资源形态" },
  { value: "3", unit: "路", label: "混合检索召回" },
  { value: "484", unit: "项", label: "单元测试守护" },
  { value: "13", unit: "个", label: "功能页面" },
];

const NAVY = "hsl(201 100% 13%)";

export default function HeroLanding() {
  return (
    <div className="relative min-h-screen bg-background" style={{ fontFamily: "var(--font-body)" }}>
      {/* 固定视频背景：无遮罩，hero 一屏完整透出 */}
      <video
        className="fixed inset-0 z-0 h-full w-full object-cover"
        src="/hero-loop.mp4"
        autoPlay
        loop
        muted
        playsInline
      />

      {/* 第一屏：导航 + 诗意主张，全部悬浮在纯净视频上 */}
      <section className="relative z-10 flex h-[100svh] flex-col text-foreground">
        <nav className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-6 sm:px-8">
          <BrandMark size={30} />
          <div className="hidden items-center gap-8 md:flex">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm transition-colors ${
                  link.active
                    ? "text-foreground"
                    : "text-foreground/60 hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <Link
            href="/chat"
            className="liquid-glass rounded-full px-6 py-2.5 text-sm text-foreground transition-transform hover:scale-[1.03]"
          >
            进入工作台
          </Link>
        </nav>

        <div className="flex flex-1 flex-col items-center justify-center px-6 pb-16 text-center">
          <h1
            className="animate-fade-rise max-w-5xl text-5xl font-normal leading-[1.18] tracking-[-0.02em] sm:text-6xl md:text-7xl"
            style={{ fontFamily: "var(--font-display)" }}
          >
            让每一次学习，
            <br />
            都被<em className="not-italic text-glass-cyan">记住</em>、被
            <em className="not-italic text-glass-cyan">进化</em>。
          </h1>

          <p className="animate-fade-rise-delay mt-8 max-w-2xl text-base leading-relaxed text-foreground/75 sm:text-lg">
            ReflexLearn 是一套会自我反思的学习系统——六个智能体协作规划你的路径，
            生成文档、导图、代码、题目、阅读与视频，而每一次对话，都在沉淀为更懂你的经验。
          </p>

          <div className="animate-fade-rise-delay-2 mt-12 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/chat"
              className="liquid-glass cursor-pointer rounded-full px-12 py-4.5 text-base text-foreground transition-transform hover:scale-[1.03]"
            >
              开始学习之旅
            </Link>
            <a
              href="#capabilities"
              className="rounded-full px-6 py-4.5 text-sm text-foreground/60 transition-colors hover:text-foreground"
            >
              了解四大能力 ↓
            </a>
          </div>
        </div>
      </section>

      {/* 白色内容面板：从视频下方滚上来，与第一屏形成明暗割裂 */}
      <div className="relative z-10 rounded-t-[44px] bg-[#f7f5f0] text-slate-900 shadow-[0_-24px_80px_rgba(0,0,0,0.35)]">
        {/* 能力区块 */}
        <section id="capabilities" className="mx-auto max-w-7xl px-6 pb-24 pt-20 sm:px-8">
          <p className="text-sm tracking-[0.3em] text-cyan-700">CAPABILITIES</p>
          <h2
            className="mt-3 text-3xl sm:text-4xl"
            style={{ fontFamily: "var(--font-display)", color: NAVY }}
          >
            一个会成长的学习工作台
          </h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {CAPABILITIES.map((cap) => (
              <article
                key={cap.title}
                className="rounded-[20px] border border-slate-200/80 bg-white p-6 transition-all duration-200 hover:-translate-y-1 hover:shadow-[0_18px_50px_rgba(2,44,66,0.10)]"
              >
                <CapabilityIcon kind={cap.kind} />
                <h3 className="mt-5 text-lg font-medium" style={{ color: NAVY }}>
                  {cap.title}
                </h3>
                <p className="mt-2.5 text-sm leading-relaxed text-slate-600">{cap.desc}</p>
              </article>
            ))}
          </div>
        </section>

        {/* 数据带 */}
        <section className="border-y border-slate-200 bg-white/60">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-y-10 px-6 py-14 sm:px-8 lg:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label} className="text-center">
                <p
                  className="text-5xl"
                  style={{ fontFamily: "var(--font-display)", color: NAVY }}
                >
                  {s.value}
                  <span className="ml-1 text-xl text-slate-400">{s.unit}</span>
                </p>
                <p className="mt-2 text-sm text-slate-500">{s.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* 页脚 */}
        <footer className="mx-auto max-w-7xl px-6 pb-10 pt-16 sm:px-8">
          <div className="flex flex-col gap-10 md:flex-row md:items-start md:justify-between">
            <div className="max-w-sm">
              <span style={{ color: NAVY }}>
                <BrandMark size={26} />
              </span>
              <p className="mt-4 text-sm leading-relaxed text-slate-500">
                自进化学习多智能体系统——以反思记忆、混合检索与个性化路径，
                陪你把每一个学习目标走完。
              </p>
            </div>
            <div className="flex gap-16">
              <div>
                <p className="text-sm font-medium" style={{ color: NAVY }}>
                  产品
                </p>
                <ul className="mt-3 space-y-2 text-sm text-slate-500">
                  <li>
                    <Link href="/chat" className="transition-colors hover:text-slate-900">
                      对话工作区
                    </Link>
                  </li>
                  <li>
                    <Link href="/mistakes" className="transition-colors hover:text-slate-900">
                      错题本
                    </Link>
                  </li>
                  <li>
                    <Link href="/growth" className="transition-colors hover:text-slate-900">
                      成长档案
                    </Link>
                  </li>
                </ul>
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: NAVY }}>
                  探索
                </p>
                <ul className="mt-3 space-y-2 text-sm text-slate-500">
                  <li>
                    <Link
                      href="/tracks/ai-programming"
                      className="transition-colors hover:text-slate-900"
                    >
                      学习赛道
                    </Link>
                  </li>
                  <li>
                    <Link href="/design" className="transition-colors hover:text-slate-900">
                      设计系统
                    </Link>
                  </li>
                </ul>
              </div>
            </div>
          </div>
          <div className="mt-12 flex flex-col gap-2 border-t border-slate-200 pt-6 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">
            <p>ReflexLearn · 自进化学习多智能体系统</p>
            <p>LangGraph · FastAPI · Qdrant · Neo4j · Kafka · Next.js 15</p>
          </div>
        </footer>
      </div>
    </div>
  );
}
