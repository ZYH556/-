"use client";

import { useState } from "react";
import { PlaySquare } from "lucide-react";

interface ResourceEmbedProps {
  type: string;
  embedUrl: string;
  title: string;
}

/* 外部视频站内播放：仅 external_video + embed_url 渲染。
   默认不挂 iframe（不自动外呼 B 站、不泄漏 referrer），用户点击才加载——
   贴合 metadata_only / embed_or_redirect_only 红线：默认只持有元数据。 */
export function ResourceEmbed({ type, embedUrl, title }: ResourceEmbedProps) {
  const [playing, setPlaying] = useState(false);
  if (type !== "external_video" || !embedUrl) return null;

  const src = `${embedUrl}${embedUrl.includes("?") ? "&" : "?"}autoplay=0&danmaku=0`;

  return (
    <div className="ws-card overflow-hidden">
      <div className="relative aspect-video bg-[var(--ws-ink)]">
        {playing ? (
          <iframe
            src={src}
            title={title}
            className="absolute inset-0 h-full w-full"
            allowFullScreen
            referrerPolicy="no-referrer"
            sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"
          />
        ) : (
          <button
            type="button"
            onClick={() => setPlaying(true)}
            className="group absolute inset-0 flex flex-col items-center justify-center gap-3 text-white/90 transition-colors hover:text-white"
          >
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/15 backdrop-blur transition-transform group-hover:scale-105">
              <PlaySquare size={30} aria-hidden />
            </span>
            <span className="text-sm font-medium">在站内播放（来自 B 站）</span>
          </button>
        )}
      </div>
      <p className="px-4 py-2.5 text-xs leading-5 text-slate-500">
        外部视频仅以官方播放器嵌入，不下载或转存内容；点击才加载播放器。
      </p>
    </div>
  );
}
