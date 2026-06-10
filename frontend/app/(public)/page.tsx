import { GlassButton, GlassCard, GlassPanel } from "@/components/glass";
import { publicTracks } from "@/lib/nav";

export default function PublicHome() {
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-10 text-slate-100">
      <GlassPanel strong className="mb-6 grid gap-5 md:grid-cols-[1.2fr_0.8fr]">
        <section>
          <p className="text-sm font-medium text-cyan-200">ReflexLearn</p>
          <h1 className="mt-2 text-4xl font-semibold text-white">自进化学习平台</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
            公共内容生态、AI 个性化引擎和个人学习数据在同一个工作台里协作。
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <GlassButton href="/chat" variant="primary">进入工作台</GlassButton>
            <GlassButton href="/design" variant="ghost">设计系统</GlassButton>
          </div>
        </section>
        <GlassCard tone="aurora" eyebrow="M7" title="自进化飞轮">
          记忆进化、元认知改进、协作深化和 LoRA 慢回路将按波次继续接入。
        </GlassCard>
      </GlassPanel>

      <section className="grid gap-4 md:grid-cols-3">
        {publicTracks.map((track) => (
          <GlassCard key={track.id} tone="mint" eyebrow="track" title={track.label}>
            <p className="mb-4 text-sm text-slate-300">{track.description}</p>
            <GlassButton href={track.href}>查看赛道</GlassButton>
          </GlassCard>
        ))}
      </section>
    </main>
  );
}
