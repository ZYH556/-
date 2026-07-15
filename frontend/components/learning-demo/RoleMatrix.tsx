import { roleViews } from "@/lib/learningDemo";
import { Tag, WsCard } from "@/components/workspace";

export function RoleMatrix() {
  return (
    <WsCard eyebrow="Roles" title="分角色学习系统">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {roleViews.map((item) => (
          <article
            key={item.role}
            className="border border-[var(--ws-line)] bg-[#fbfaf7] p-4"
          >
            <Tag tone={item.role === "student" ? "accent" : item.role === "admin" ? "warning" : "neutral"}>
              {item.title}
            </Tag>
            <p className="mt-3 text-sm leading-6 text-slate-600">{item.responsibility}</p>
            <ul className="mt-4 space-y-2 text-xs text-slate-500">
              {item.actions.map((action) => (
                <li key={action} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--ws-accent)]" />
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </WsCard>
  );
}
