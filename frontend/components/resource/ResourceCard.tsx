import type { ResourceCard as Card } from "@/lib/types";
import { MarkdownView } from "../cards/MarkdownView";
import { MindmapCard } from "../cards/MindmapCard";

const TYPE_META: Record<string, { label: string; color: string }> = {
  doc: { label: "讲解文档", color: "bg-blue-100 text-blue-700" },
  quiz: { label: "练习题", color: "bg-amber-100 text-amber-700" },
  mindmap: { label: "思维导图", color: "bg-green-100 text-green-700" },
  code: { label: "代码案例", color: "bg-purple-100 text-purple-700" },
  reading: { label: "拓展阅读", color: "bg-teal-100 text-teal-700" },
  video: { label: "多模态视频", color: "bg-orange-100 text-orange-700" },
  debate: { label: "辩论结论", color: "bg-rose-100 text-rose-700" },
};

export function ResourceCard({ card }: { card: Card }) {
  const meta = TYPE_META[card.type] || {
    label: card.type,
    color: "bg-slate-100 text-slate-700",
  };

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${meta.color}`}
        >
          {meta.label}
        </span>
        <span className="text-xs text-slate-400">{card.task_id}</span>
      </div>
      {card.type === "mindmap" ? (
        <MindmapCard content={card.content} />
      ) : card.type === "video" ? (
        <div className="space-y-3">
          <div className="flex aspect-video items-center justify-center rounded-lg bg-gradient-to-br from-orange-400 to-rose-400 text-white">
            <div className="flex flex-col items-center gap-1">
              <span className="text-4xl leading-none">▶</span>
              <span className="text-xs opacity-90">视频生成占位 · 分镜脚本就绪</span>
            </div>
          </div>
          <MarkdownView content={card.content} />
        </div>
      ) : (
        <MarkdownView content={card.content} />
      )}
    </article>
  );
}
