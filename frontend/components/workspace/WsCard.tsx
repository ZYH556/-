import type { HTMLAttributes, ReactNode } from "react";

type WsCardProps = HTMLAttributes<HTMLElement> & {
  eyebrow?: string;
  title?: string;
  action?: ReactNode;
};

export function WsCard({
  eyebrow,
  title,
  action,
  className,
  children,
  ...props
}: WsCardProps) {
  return (
    <section className={`ws-card p-5 ${className ?? ""}`} {...props}>
      {eyebrow || title || action ? (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div className="min-w-0">
            {eyebrow ? <p className="ws-eyebrow">{eyebrow}</p> : null}
            {title ? (
              <h3 className="mt-1 font-medium text-[var(--ws-ink)]">{title}</h3>
            ) : null}
          </div>
          {action}
        </header>
      ) : null}
      {children}
    </section>
  );
}
