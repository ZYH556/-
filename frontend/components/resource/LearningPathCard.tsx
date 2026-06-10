import type { LearningPath } from "@/lib/types";

const TYPE_LABEL: Record<string, string> = {
  doc: "讲解文档",
  quiz: "练习题",
  mindmap: "思维导图",
  code: "代码案例",
  reading: "拓展阅读",
  video: "多模态视频",
  debate: "辩论结论",
};

export function LearningPathCard({ path }: { path: LearningPath }) {
  if (!path?.steps || path.steps.length === 0) return null;

  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5 shadow-sm">
      <div className="mb-1 flex items-center gap-2">
        <span className="rounded-full bg-indigo-600 px-2.5 py-0.5 text-xs font-medium text-white">
          个性化学习路径
        </span>
        <span className="text-xs text-slate-500">{path.steps.length} 步</span>
      </div>
      {path.summary && (
        <p className="mb-3 text-sm text-slate-600">{path.summary}</p>
      )}

      <ol className="space-y-3">
        {path.steps.map((s) => (
          <li key={`${s.sequence}-${s.task_id}`} className="flex gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
              {s.sequence}
            </span>
            <div className="flex-1 rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {TYPE_LABEL[s.resource_type] || s.resource_type}
                </span>
                {s.concept && (
                  <span className="text-sm font-medium text-slate-800">
                    {s.concept}
                  </span>
                )}
                {typeof s.difficulty === "number" && (
                  <span className="ml-auto text-xs text-slate-400">
                    难度 {s.difficulty.toFixed(1)}
                  </span>
                )}
              </div>
              {s.objective && (
                <p className="mt-1.5 text-sm text-slate-700">🎯 {s.objective}</p>
              )}
              {s.rationale && (
                <p className="mt-1 text-xs text-slate-500">💡 {s.rationale}</p>
              )}
            </div>
          </li>
        ))}
      </ol>

      {path.strategy && (
        <p className="mt-3 border-t border-indigo-100 pt-2 text-xs text-slate-400">
          排序策略：{path.strategy}
        </p>
      )}
    </section>
  );
}
