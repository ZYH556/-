"use client";

import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";

import { resourceMeta } from "@/components/workspace";
import type { SpaceResource } from "@/lib/types";

export function SpaceResourceList({ resources }: { resources: SpaceResource[] }) {
  const [filter, setFilter] = useState("all");
  const [openId, setOpenId] = useState("");

  const types = useMemo(
    () => Array.from(new Set(resources.map((r) => r.type))),
    [resources],
  );
  const shown = useMemo(
    () => (filter === "all" ? resources : resources.filter((r) => r.type === filter)),
    [resources, filter],
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => setFilter("all")}
          className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
            filter === "all"
              ? "border-[var(--ws-navy)] bg-[var(--ws-navy)] text-white"
              : "border-[var(--ws-line-strong)] bg-white text-slate-600 hover:border-[var(--ws-navy)]"
          }`}
        >
          全部 {resources.length}
        </button>
        {types.map((t) => {
          const meta = resourceMeta(t);
          const n = resources.filter((r) => r.type === t).length;
          return (
            <button
              key={t}
              type="button"
              onClick={() => setFilter(t)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                filter === t
                  ? "border-[var(--ws-navy)] bg-[var(--ws-navy)] text-white"
                  : "border-[var(--ws-line-strong)] bg-white text-slate-600 hover:border-[var(--ws-navy)]"
              }`}
            >
              {meta.label} {n}
            </button>
          );
        })}
      </div>

      <ul className="space-y-2">
        {shown.map((res) => {
          const meta = resourceMeta(res.type);
          const Icon = meta.icon;
          const open = openId === res.resource_id;
          return (
            <li key={res.resource_id} className="rounded-xl border border-[var(--ws-line)] bg-white">
              <button
                type="button"
                onClick={() => setOpenId(open ? "" : res.resource_id)}
                className="flex w-full items-center gap-3 p-3 text-left"
              >
                <span
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${meta.chipClass}`}
                >
                  <Icon size={15} aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-[var(--ws-ink)]">
                    {res.title || meta.label}
                  </span>
                  {res.concept ? (
                    <span className="block text-xs text-slate-500">{res.concept}</span>
                  ) : null}
                </span>
                <ChevronDown
                  size={15}
                  className={`shrink-0 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
                  aria-hidden
                />
              </button>
              {open ? (
                <div className="border-t border-[var(--ws-line)] px-4 py-3">
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs leading-relaxed text-slate-700">
                    {res.content}
                  </pre>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
