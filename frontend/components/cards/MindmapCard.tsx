"use client";

import { useEffect, useRef, useState } from "react";

/**
 * 渲染后端 mindmap_gen 产出的 Mermaid mindmap 语法。
 * mermaid 在客户端动态 import（避免 SSR 阶段触碰 document）；渲染失败降级为原始代码块。
 */
export function MindmapCard({ content }: { content: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const code = extractMermaid(content);

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    const id = `mmd-${Math.random().toString(36).slice(2)}`;

    import("mermaid")
      .then(({ default: mermaid }) => {
        mermaid.initialize({ startOnLoad: false, theme: "default" });
        return mermaid.render(id, code);
      })
      .then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (failed) {
    return (
      <pre className="overflow-x-auto rounded-lg bg-slate-100 p-3 text-xs text-slate-700">
        {code}
      </pre>
    );
  }
  return <div ref={ref} className="flex justify-center overflow-x-auto" />;
}

function extractMermaid(content: string): string {
  const fence = content.match(/```(?:mermaid)?\s*([\s\S]*?)```/);
  return (fence ? fence[1] : content).trim();
}
