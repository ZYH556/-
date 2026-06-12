import type { ProfileSignal, ReviewItem } from "./types";

export function ProfileSignals({ signals }: { signals: ProfileSignal[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-[var(--ws-ink)]">系统已学习到的偏好</h2>
      <dl className="divide-y divide-[var(--ws-line)] bg-white">
        {signals.map((signal) => (
          <div key={signal.label} className="px-4 py-3">
            <dt className="text-xs text-slate-500">{signal.label}</dt>
            <dd className="mt-1 text-sm leading-6 text-[var(--ws-ink)]">{signal.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function ReviewQueue({ items }: { items: ReviewItem[] }) {
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-[var(--ws-ink)]">复习提醒</h2>
      <ol className="space-y-2">
        {items.map((item) => (
          <li key={item.topic} className="bg-white px-4 py-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-medium text-[var(--ws-ink)]">{item.topic}</h3>
              <span className="shrink-0 text-xs text-slate-500">{item.dueLabel}</span>
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-500">{item.reason}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
