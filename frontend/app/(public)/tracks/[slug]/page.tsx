import { GlassButton, GlassCard, GlassPanel } from "@/components/glass";
import { publicTracks } from "@/lib/nav";

interface TrackPageProps {
  params: Promise<{ slug: string }>;
}

export default async function TrackPage({ params }: TrackPageProps) {
  const { slug } = await params;
  const track = publicTracks.find((item) => item.id === slug) ?? publicTracks[0];

  return (
    <main className="mx-auto min-h-screen max-w-5xl px-4 py-10 text-slate-100">
      <GlassPanel strong>
        <p className="text-sm font-medium text-cyan-200">公共赛道馆</p>
        <h1 className="mt-2 text-3xl font-semibold text-white">{track.label}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{track.description}</p>
        <div className="mt-5 flex flex-wrap gap-2">
          <GlassButton href="/chat" variant="primary">用个人智能体学习</GlassButton>
          <GlassButton href="/">返回首页</GlassButton>
        </div>
      </GlassPanel>

      <section className="mt-5 grid gap-4 md:grid-cols-3">
        {["公共课程", "公共知识库", "推荐路线"].map((title) => (
          <GlassCard key={title} tone="aurora" eyebrow="wave 2" title={title}>
            TODO: docs/14 波次 2 接入真实公共内容与课程数据。
          </GlassCard>
        ))}
      </section>
    </main>
  );
}
