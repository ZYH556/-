"use client";

import { usePathname } from "next/navigation";
import { AuthGate } from "../_components/AuthGate";
import { AuthSessionProvider } from "@/lib/authContext";
import { workspaceNavItems } from "@/lib/nav";
import { GlassButton, GlassPanel, GlassSidebar } from "@/components/glass";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthGate>
      {(session) => (
        <AuthSessionProvider session={session}>
          <main className="min-h-screen px-4 py-6 text-slate-100">
            <div className="mx-auto grid max-w-7xl gap-5 lg:grid-cols-[280px_1fr]">
              <GlassSidebar
                title="ReflexLearn"
                subtitle={`${session.auth.user.tenant_id} · ${session.auth.user.role}`}
                items={workspaceNavItems.map((item) => ({
                  id: item.id,
                  label: item.label,
                  href: item.href,
                  active: pathname === item.href,
                }))}
                footer={<GlassButton onClick={session.onLogout}>退出</GlassButton>}
              />
              <GlassPanel strong className="min-h-[calc(100vh-3rem)]">
                {children}
              </GlassPanel>
            </div>
          </main>
        </AuthSessionProvider>
      )}
    </AuthGate>
  );
}
