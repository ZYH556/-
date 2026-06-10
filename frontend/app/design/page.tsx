"use client";

import {
  GlassButton,
  GlassCard,
  GlassModal,
  GlassPanel,
  GlassSidebar,
  type GlassSidebarItem,
} from "@/components/glass";

const sidebarItems: GlassSidebarItem[] = [
  { id: "space", label: "学习空间", active: true },
  { id: "chat", label: "对话工作区" },
  { id: "plan", label: "学习路径" },
  { id: "growth", label: "成长档案" },
];

const swatches = [
  { name: "surface", className: "bg-glass-surface" },
  { name: "strong", className: "bg-glass-surface-strong" },
  { name: "cyan", className: "bg-glass-cyan" },
  { name: "mint", className: "bg-glass-mint" },
  { name: "ember", className: "bg-glass-ember" },
];

export default function DesignPage() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-10 text-slate-100">
      <section className="mb-8">
        <p className="text-sm font-medium text-cyan-200">ReflexLearn Design System</p>
        <h1 className="mt-2 text-4xl font-semibold text-white">灵动玻璃组件库</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
          暗色优先的玻璃材质、景深、高光、圆角和 CSS 动效 token。该页面只展示设计系统，
          不接入后端数据。
        </p>
      </section>

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        <GlassSidebar
          title="ReflexLearn"
          subtitle="个人学习工作台"
          items={sidebarItems}
          footer={<p className="text-xs text-slate-300">自进化快回路已就绪</p>}
        />

        <div className="space-y-5">
          <GlassPanel strong className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
            <div>
              <p className="text-xs font-medium uppercase text-cyan-200/80">
                glass panel
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">
                公共资源与个人智能体分层呈现
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                面板用于工作台主容器、资源详情和状态区，支持更强的玻璃材质以压住复杂背景。
              </p>
              <div className="mt-5 flex flex-wrap gap-2">
                <GlassButton variant="primary">开始学习</GlassButton>
                <GlassButton active>查看路径</GlassButton>
                <GlassButton variant="ghost">稍后处理</GlassButton>
              </div>
            </div>
            <GlassCard tone="aurora" eyebrow="live metric" title="记忆复用度">
              <div className="flex items-end gap-3">
                <span className="text-5xl font-semibold text-white">72%</span>
                <span className="pb-2 text-xs text-cyan-100">本周提升 8%</span>
              </div>
            </GlassCard>
          </GlassPanel>

          <section className="grid gap-4 md:grid-cols-3">
            <GlassCard tone="aurora" eyebrow="card" title="学习目标">
              玻璃卡片用于承载单个资源、路径节点或智能体状态。
            </GlassCard>
            <GlassCard tone="mint" eyebrow="card" title="知识图谱">
              多层半透明背景与边缘高光区分信息层级。
            </GlassCard>
            <GlassCard tone="ember" eyebrow="card" title="错题闭环">
              CSS-only 微动效适配 MVP，后续再按需扩展复杂编排。
            </GlassCard>
          </section>

          <GlassPanel className="grid gap-4 md:grid-cols-2">
            <div>
              <h2 className="text-lg font-semibold text-white">Token 色板</h2>
              <p className="mt-1 text-sm text-slate-300">
                Tailwind v4 `@theme` 输出的玻璃颜色 token。
              </p>
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                {swatches.map((swatch) => (
                  <div key={swatch.name} className="space-y-2">
                    <div
                      className={`h-16 rounded-glass-card border border-white/15 ${swatch.className}`}
                    />
                    <p className="text-xs text-slate-300">{swatch.name}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative min-h-64 overflow-hidden rounded-glass-panel border border-white/10">
              <GlassModal
                contained
                open
                title="GlassModal"
                onClose={() => undefined}
                action={<GlassButton variant="primary">确认</GlassButton>}
              >
                受控弹层组件由调用方管理 open/onClose/action，适合后续工作台复用。
              </GlassModal>
            </div>
          </GlassPanel>
        </div>
      </div>
    </main>
  );
}
