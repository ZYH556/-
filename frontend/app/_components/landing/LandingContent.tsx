import Link from "next/link";
import { BrandMark } from "../BrandMark";

const NAVY = "#061B24";

const CAPABILITIES = [
  ["学习画像", "专业、年级、学习风格、错题表现和目标方向会被整理成持续更新的个人画像。"],
  ["路径规划", "系统把目标拆成章节顺序、重点、难度、预计耗时和当前学习位置。"],
  ["资源生成", "文档、导图、题库、阅读、视频脚本和代码实操由多 Agent 协作生成。"],
  ["成长反馈", "课程讨论、AI 辅导、错题复盘和差距报告共同推动下一轮学习计划。"],
];

const METRICS = [
  ["6", "资源形态"],
  ["12", "画像维度"],
  ["3", "检索召回"],
  ["24/7", "智能辅导"],
];

const FLOW = [
  ["01", "理解目标", "从专业背景、学习目的和当前短板开始，而不是直接生成一份通用计划。"],
  ["02", "组织路线", "把目标拆到章节、练习、资源和验收节点，形成可以每天推进的路线。"],
  ["03", "生成材料", "围绕当前路径补齐课程文档、思维导图、题库、拓展阅读和代码实操。"],
  ["04", "复盘进化", "错题、讨论、测评和差距报告会回流到画像，更新下一步建议。"],
];

const STORIES = [
  ["profile", "系统先理解你。", "学习画像把目标、薄弱点、错题表现和学习风格放在同一个上下文里，后续路径和资源才有依据。"],
  ["path", "目标会变成路线。", "章节、重点、难度和预计耗时被组织成可推进的学习路径，学习者知道今天应该做什么。"],
  ["resource", "资源按路径生成。", "多 Agent 根据当前章节生成文档、导图、练习、拓展阅读、视频脚本和代码实操。"],
  ["feedback", "反馈会改变下一步。", "课程讨论、AI 回复、错题复盘和差距报告回流画像，让计划持续更新。"],
];

function MediaSlot({ label }: { label: string }) {
  return (
    <div className="relative aspect-[1.16] overflow-hidden border border-white/12 bg-white/[0.055]">
      <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(125,211,252,0.16),transparent_44%),radial-gradient(circle_at_72%_18%,rgba(255,255,255,0.18),transparent_28%)]" />
      <div className="absolute inset-x-8 top-8 flex items-center justify-between">
        <span className="h-px flex-1 bg-white/18" />
        <span className="ml-5 font-mono text-[11px] uppercase tracking-[0.24em] text-cyan-100/70">
          {label}
        </span>
      </div>
      <div className="absolute bottom-8 left-8 right-8 h-20 border-t border-white/14" />
    </div>
  );
}

function ProductPlaceholder({ type }: { type: string }) {
  if (type === "profile") {
    return (
      <div className="relative min-h-[360px] overflow-hidden bg-[#E8F1F3] p-8">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_75%_20%,rgba(6,27,36,0.14),transparent_30%)]" />
        <div className="relative grid h-full gap-8 sm:grid-cols-[0.8fr_1.2fr]">
          <div className="self-end">
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-cyan-900/60">profile</p>
            <div className="mt-8 aspect-square max-w-[220px] border border-[#061B24]/18 bg-white/35" />
          </div>
          <div className="space-y-5 self-center">
            {["知识基础", "薄弱环节", "学习风格", "目标方向"].map((item, index) => (
              <div key={item} className="grid grid-cols-[84px_1fr] items-center gap-5">
                <span className="text-sm text-[#1C313A]">{item}</span>
                <span className="h-2 bg-[#061B24]/10">
                  <span className="block h-full bg-cyan-700/70" style={{ width: `${58 + index * 9}%` }} />
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (type === "path") {
    return (
      <div className="relative min-h-[360px] overflow-hidden bg-[#F0EDE4] p-8">
        <div className="absolute left-16 top-14 h-[72%] w-px bg-[#061B24]/18" />
        <div className="relative space-y-8">
          {["前端基础回顾", "组件通信", "数据结构", "Agent 系统开发"].map((item, index) => (
            <div key={item} className="grid grid-cols-[44px_1fr] items-start gap-6">
              <span className="grid size-11 place-items-center bg-[#061B24] font-mono text-xs text-white">0{index + 1}</span>
              <div className="border-t border-[#061B24]/14 pt-4">
                <p className="text-xl" style={{ fontFamily: "var(--font-display)", color: NAVY }}>{item}</p>
                <p className="mt-2 text-sm text-slate-600">{index < 2 ? "基础 · 3 小时" : "进阶 · 5 小时"}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "resource") {
    return (
      <div className="relative min-h-[360px] overflow-hidden bg-[#071C2B] p-8 text-white">
        <div className="grid h-full content-center gap-5">
          {["课程文档", "思维导图", "练习题库", "代码实操"].map((item, index) => (
            <div key={item} className="grid grid-cols-[96px_1fr_56px] items-center gap-5 border-t border-white/12 pt-5">
              <span className="font-mono text-xs text-cyan-200">Agent 0{index + 1}</span>
              <span className="text-lg" style={{ fontFamily: "var(--font-display)" }}>{item}</span>
              <span className="h-1 bg-cyan-200/70" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-[360px] overflow-hidden bg-[#DCE9EF] p-8">
      <div className="grid h-full gap-8 sm:grid-cols-[1fr_1fr]">
        <div className="self-end">
          <p className="text-[84px] leading-none" style={{ fontFamily: "var(--font-display)", color: NAVY }}>62</p>
          <p className="mt-2 text-sm text-slate-600">行业匹配度</p>
        </div>
        <div className="space-y-5 self-center">
          {["优势能力", "待提升", "重点关注"].map((item, index) => (
            <div key={item} className="border-t border-[#061B24]/16 pt-4">
              <p className="text-sm text-slate-500">{item}</p>
              <p className="mt-1 text-2xl" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
                {index === 0 ? "代码开发" : index === 1 ? "Agent 开发" : "算法结构"}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function LandingContent() {
  return (
    <div className="relative z-10 overflow-hidden rounded-t-[42px] bg-[#f6f3ec] text-slate-900 shadow-[0_-24px_80px_rgba(0,0,0,0.28)]">
      <section id="capabilities" className="mx-auto grid max-w-7xl gap-16 px-6 pb-20 pt-24 sm:px-8 lg:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-800">Learning System</p>
          <h2 className="mt-5 max-w-xl text-[48px] leading-[1.02] sm:text-[64px]" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
            学习不是页面跳转，而是一条会更新的路线。
          </h2>
        </div>
        <div className="max-w-2xl self-end">
          <p className="text-xl leading-[1.75] text-[#1C313A]">
            ReflexLearn 从你的目标出发，建立画像、规划路径、生成资源、追踪错题，并把每一次学习后的反馈写回系统。
            它不只是回答问题，而是让学习过程逐步变得更贴近你。
          </p>
          <div className="mt-10 flex flex-wrap gap-5">
            <Link href="/chat" className="border-b border-[#061B24] pb-1 text-sm font-medium text-[#061B24] transition-opacity hover:opacity-60">
              开始学习规划
            </Link>
            <a href="#flow" className="border-b border-slate-400 pb-1 text-sm font-medium text-slate-600 transition-opacity hover:opacity-60">
              查看系统链路
            </a>
          </div>
        </div>
      </section>

      <section className="px-6 sm:px-8">
        <div className="mx-auto grid max-w-7xl border-y border-[#061B24]/16 md:grid-cols-4">
          {CAPABILITIES.map(([title, desc]) => (
            <div key={title} className="border-b border-[#061B24]/12 py-9 md:border-b-0 md:border-r md:px-8 last:md:border-r-0">
              <h3 className="text-[28px] leading-none" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
                {title}
              </h3>
              <p className="mt-5 max-w-xs text-sm leading-7 text-slate-600">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-12 px-6 py-24 sm:px-8 lg:grid-cols-[1fr_1.2fr]">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-800">Signal</p>
          <h2 className="mt-4 text-[42px] leading-[1.05]" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
            少量真实指标，比堆满卖点更可信。
          </h2>
        </div>
        <div className="grid grid-cols-2 gap-x-10 gap-y-12 sm:grid-cols-4">
          {METRICS.map(([value, label]) => (
            <div key={label}>
              <p className="text-[56px] leading-none" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
                {value}
              </p>
              <p className="mt-3 text-sm text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="px-6 pb-24 sm:px-8">
        <div className="mx-auto max-w-7xl border-t border-[#061B24]/16">
          {STORIES.map(([type, title, desc], index) => (
            <div key={type} className="grid gap-10 border-b border-[#061B24]/16 py-12 lg:grid-cols-[0.82fr_1.18fr]">
              <div className="max-w-md">
                <p className="font-mono text-xs uppercase tracking-[0.24em] text-cyan-800">0{index + 1}</p>
                <h3 className="mt-5 text-[42px] leading-[1.05]" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
                  {title}
                </h3>
                <p className="mt-6 text-base leading-8 text-[#1C313A]">{desc}</p>
              </div>
              <ProductPlaceholder type={type} />
            </div>
          ))}
        </div>
      </section>

      <section id="flow" className="bg-[#061B24] px-6 py-24 text-white sm:px-8">
        <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[0.86fr_1.14fr]">
          <div className="lg:sticky lg:top-24 lg:self-start">
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-cyan-200">Agent Workflow</p>
            <h2 className="mt-5 text-[44px] leading-[1.03] sm:text-[56px]" style={{ fontFamily: "var(--font-display)" }}>
              智能体藏在流程里。
            </h2>
            <p className="mt-7 max-w-sm text-sm leading-7 text-slate-300">
              下方预留给 Agent 流水线视频、资源生成过程录屏，或学习路径生成动效。
            </p>
            <div className="mt-10">
              <MediaSlot label="agent motion" />
            </div>
          </div>
          <div className="divide-y divide-white/14 border-y border-white/14">
            {FLOW.map(([step, title, desc]) => (
              <div key={step} className="grid gap-8 py-10 sm:grid-cols-[72px_1fr]">
                <p className="font-mono text-sm text-cyan-200">{step}</p>
                <div>
                  <h3 className="text-[32px] leading-none" style={{ fontFamily: "var(--font-display)" }}>{title}</h3>
                  <p className="mt-5 max-w-xl text-base leading-8 text-slate-300">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-[#DDEBF0] px-6 py-24 sm:px-8">
        <div className="mx-auto grid max-w-7xl gap-14 lg:grid-cols-[1.05fr_0.95fr]">
          <h2 className="max-w-3xl text-[48px] leading-[1.02] sm:text-[68px]" style={{ fontFamily: "var(--font-display)", color: NAVY }}>
            下一步，始终清楚。
          </h2>
          <div className="self-end text-[#1E3A45]">
            <p className="text-lg leading-8">
              后续页面会承载更多具体界面：课程播放、AI 评论回复、导师匹配、路径规划、资源生成、错题复盘和行业能力对比。
              首页只负责建立清晰的产品气质，让用户理解这不是内容集合，而是一套能持续推进学习的系统。
            </p>
            <Link href="/growth" className="mt-9 inline-block border-b border-[#061B24] pb-1 text-sm font-medium text-[#061B24] transition-opacity hover:opacity-60">
              查看成长档案
            </Link>
          </div>
        </div>
      </section>

      <footer className="bg-[#061B24] px-6 pb-10 pt-14 text-white sm:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-12 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <BrandMark size={28} />
            <p className="mt-5 text-sm leading-7 text-slate-300">
              ReflexLearn 用智能体协作、混合检索、学习画像和反思记忆，把目标推进成路径，把练习沉淀成成长。
            </p>
          </div>
          <div className="grid gap-12 text-sm text-slate-300 sm:grid-cols-2">
            <div className="space-y-3">
              <Link href="/chat" className="block hover:text-white">AI 辅导</Link>
              <Link href="/plan" className="block hover:text-white">学习路径</Link>
              <Link href="/resources" className="block hover:text-white">资源生成</Link>
            </div>
            <div className="space-y-3">
              <Link href="/spaces" className="block hover:text-white">学习空间</Link>
              <Link href="/mistakes" className="block hover:text-white">错题复盘</Link>
              <Link href="/growth" className="block hover:text-white">成长档案</Link>
            </div>
          </div>
        </div>
        <div className="mx-auto mt-12 flex max-w-7xl justify-between border-t border-white/10 pt-5 text-sm text-slate-400">
          <p>ReflexLearn</p>
          <p>Personal learning system</p>
        </div>
      </footer>
    </div>
  );
}
