type TodayHeroProps = {
  greeting: string;
  learner: string;
  goal: string;
  summary: string;
  progress: number;
};

export function TodayHero({ greeting, learner, goal, summary, progress }: TodayHeroProps) {
  const percent = Math.round(progress * 100);

  return (
    <header className="grid gap-6 border-b border-[var(--ws-line)] pb-8 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
      <div>
        <p className="text-xs font-medium text-slate-500">{learner}</p>
        <h1 className="mt-3 text-3xl font-medium leading-tight text-[var(--ws-ink)] sm:text-4xl">
          {greeting}
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
          当前目标：{goal}
        </p>
        <p className="mt-1 text-sm leading-6 text-slate-500">{summary}</p>
      </div>

      <div className="bg-white/65 p-4 shadow-[inset_0_1px_0_rgb(255_255_255/0.72)]">
        <div className="flex items-baseline justify-between">
          <span className="text-sm text-slate-500">当前进度</span>
          <strong className="text-2xl font-medium text-[var(--ws-ink)]">{percent}%</strong>
        </div>
        <div className="mt-4 h-2 bg-[#e7e3da]">
          <div className="h-full bg-[var(--ws-navy)]" style={{ width: `${percent}%` }} />
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          下一段学习会优先修复阻碍后续练习的概念断点。
        </p>
      </div>
    </header>
  );
}
