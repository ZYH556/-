import Link from "next/link";
import {
  BookOpenText,
  ClipboardCheck,
  ExternalLink,
  FileText,
  PlaySquare,
  type LucideIcon,
} from "lucide-react";

import type { TodayResource } from "./types";

type ResourceMeta = {
  icon: LucideIcon;
  className: string;
};

const RESOURCE_META: Record<TodayResource["type"], ResourceMeta> = {
  external_video: { icon: PlaySquare, className: "bg-rose-50 text-rose-700" },
  ai_document: { icon: FileText, className: "bg-cyan-50 text-cyan-700" },
  quiz: { icon: ClipboardCheck, className: "bg-amber-50 text-amber-700" },
  official_doc: { icon: BookOpenText, className: "bg-emerald-50 text-emerald-700" },
  oer: { icon: BookOpenText, className: "bg-indigo-50 text-indigo-700" },
  user_upload: { icon: FileText, className: "bg-slate-100 text-slate-700" },
};

type RecommendedResourcesProps = {
  resources: TodayResource[];
};

function isExternalHref(href: string): boolean {
  return href.startsWith("http://") || href.startsWith("https://");
}

function ResourceAction({ href }: { href: string }) {
  const content = (
    <>
      打开资源
      <ExternalLink size={14} aria-hidden />
    </>
  );

  if (isExternalHref(href)) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--ws-accent)] hover:text-[var(--ws-ink)]"
      >
        {content}
      </a>
    );
  }

  return (
    <Link
      href={href}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--ws-accent)] hover:text-[var(--ws-ink)]"
    >
      {content}
    </Link>
  );
}

export function RecommendedResources({ resources }: RecommendedResourcesProps) {
  return (
    <section className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--ws-accent)]">
          Resources
        </p>
        <h2 className="mt-2 text-xl font-medium text-[var(--ws-ink)]">现在最值得用的资源</h2>
      </div>

      <div className="divide-y divide-[var(--ws-line)] bg-white">
        {resources.map((resource) => {
          const meta = RESOURCE_META[resource.type];
          const Icon = meta.icon;
          return (
            <article key={resource.id} className="grid gap-4 px-4 py-5 md:grid-cols-[1fr_120px]">
              <div className="flex gap-4">
                <span
                  className={`mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center ${meta.className}`}
                >
                  <Icon size={18} aria-hidden />
                </span>
                <div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>{resource.sourceLabel}</span>
                    <span>{resource.provider}</span>
                    <span>{resource.estimatedMinutes} 分钟</span>
                  </div>
                  <h3 className="mt-2 text-base font-medium text-[var(--ws-ink)]">
                    {resource.title}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{resource.reason}</p>
                </div>
              </div>
              <div className="flex items-center md:justify-end">
                <ResourceAction href={resource.href} />
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
