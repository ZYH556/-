import { AgentProcessPanel } from "@/components/agents/AgentProcessPanel";
import { PageHeader, Tag, WsCard } from "@/components/workspace";
import { activeCourse, industryCapabilities } from "@/lib/learningDemo";

export default function IndustryPage() {
  return (
    <section className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <PageHeader
        eyebrow="Industry Profile"
        title="行业画像"
        description={`以“${activeCourse.target}”为目标岗位，将课程学习结果映射到就业能力画像。`}
      />

      <AgentProcessPanel page="industry" />

      <section className="ws-card p-8 text-center">
        <p className="ws-eyebrow">Target Role</p>
        <h2 className="ws-serif mt-3 text-3xl text-[var(--ws-ink)]">
          AI 时代，软件开发人才的核心能力画像
        </h2>
        <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          开发者正从“编码确定规则的执行者”转变为“设计智能系统的架构师”。
          当前课程主线会重点补齐 Agent 开发、大模型应用和业务方案表达。
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          {
            title: "行业应用业务方案能力",
            subtitle: "行业应用业务为什么做和做什么",
            text: "顶层设计、痛点分析、流程重塑、价值衡量指标和技术实现路径。",
          },
          {
            title: "Agent 智能体开发能力",
            subtitle: "高级形态与自动化创造",
            text: "能独立设计可运行的智能体，并让它主动完成任务而非被动响应。",
          },
          {
            title: "AI 大模型应用能力",
            subtitle: "核心引擎与部件提供什么",
            text: "智能客服、文档助手、代码生成、营销文案等真实 AI 应用能力。",
          },
        ].map((item) => (
          <WsCard key={item.title} title={item.title} eyebrow={item.subtitle}>
            <p className="text-sm leading-6 text-slate-600">{item.text}</p>
          </WsCard>
        ))}
      </div>

      <WsCard eyebrow="Capability" title="岗位能力项">
        <div className="grid gap-4 md:grid-cols-2">
          {industryCapabilities.map((item) => (
            <article key={item.title} className="border border-[var(--ws-line)] bg-[#fbfaf7] p-4">
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-medium text-[var(--ws-ink)]">{item.title}</h3>
                <Tag tone={item.status === "advantage" ? "success" : item.status === "focus" ? "danger" : "neutral"}>
                  目标 {item.target}%
                </Tag>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full rounded-full bg-[var(--ws-accent)]" style={{ width: `${item.target}%` }} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600">{item.advice}</p>
            </article>
          ))}
        </div>
      </WsCard>
    </section>
  );
}
