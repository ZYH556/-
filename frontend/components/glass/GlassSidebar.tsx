import type { ReactNode } from "react";
import { cx } from "./types";

export interface GlassSidebarItem {
  id: string;
  label: string;
  href?: string;
  icon?: ReactNode;
  active?: boolean;
}

interface GlassSidebarProps {
  title: string;
  subtitle?: string;
  items: GlassSidebarItem[];
  footer?: ReactNode;
  className?: string;
}

export function GlassSidebar({
  title,
  subtitle,
  items,
  footer,
  className,
}: GlassSidebarProps) {
  return (
    <aside
      className={cx(
        "glass-strong flex h-full min-h-[420px] w-full flex-col",
        "rounded-glass-panel p-4 shadow-glow-soft",
        className,
      )}
    >
      <header className="mb-5 px-2">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-slate-300">{subtitle}</p>}
      </header>

      <nav className="flex flex-1 flex-col gap-1">
        {items.map((item) => (
          <a
            key={item.id}
            href={item.href}
            className={cx(
              "flex items-center gap-3 rounded-glass-control px-3 py-2.5",
              "text-sm transition-glass",
              item.active
                ? "bg-white/16 text-white shadow-glow-cyan"
                : "text-slate-300 hover:bg-white/10 hover:text-white",
            )}
          >
            {item.icon && <span className="text-cyan-200">{item.icon}</span>}
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      {footer && <footer className="mt-5 border-t border-white/10 pt-4">{footer}</footer>}
    </aside>
  );
}
