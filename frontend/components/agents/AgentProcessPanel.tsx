import { pageAgentFlows, agentIconMap, type DemoAgentStep } from "@/lib/learningDemo";
import { Tag, WsCard } from "@/components/workspace";

const STATUS_COPY: Record<DemoAgentStep["status"], { label: string; tone: "success" | "accent" | "neutral" }> = {
  done: { label: "已完成", tone: "success" },
  running: { label: "调用中", tone: "accent" },
  waiting: { label: "待触发", tone: "neutral" },
};

export function AgentProcessPanel({
  page,
  title = "Agent 调用过程",
}: {
  page: keyof typeof pageAgentFlows;
  title?: string;
}) {
  const steps = pageAgentFlows[page] ?? [];
  const completed = steps.filter((step) => step.status === "done").length;

  return (
    <WsCard
      eyebrow="Trace"
      title={title}
      action={<Tag tone="accent">{completed}/{steps.length}</Tag>}
      className="ws-rise"
    >
      <ol className="grid gap-3 md:grid-cols-3">
        {steps.map((step, index) => {
          const Icon = agentIconMap[step.status];
          const status = STATUS_COPY[step.status];
          return (
            <li
              key={`${step.agent}-${step.task}`}
              className="border border-[var(--ws-line)] bg-[#fbfaf7] p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white text-[var(--ws-accent)] shadow-[0_1px_2px_rgb(5_26_36/0.06)]">
                  <Icon size={17} aria-hidden />
                </span>
                <Tag tone={status.tone}>{status.label}</Tag>
              </div>
              <p className="mt-4 text-xs text-slate-500">步骤 {index + 1}</p>
              <h3 className="mt-1 text-sm font-semibold text-[var(--ws-ink)]">
                {step.agent}
              </h3>
              <p className="mt-1 text-sm text-slate-700">{step.task}</p>
              <p className="mt-3 text-xs leading-5 text-slate-500">{step.detail}</p>
            </li>
          );
        })}
      </ol>
    </WsCard>
  );
}
