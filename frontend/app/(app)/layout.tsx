"use client";

import "./workspace.css";

import { usePathname } from "next/navigation";
import { AuthGate } from "../_components/AuthGate";
import { AuthSessionProvider } from "@/lib/authContext";
import { LearningCompanion } from "@/components/companion";
import { SideNav } from "@/components/workspace";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AuthGate>
      {(session) => (
        <AuthSessionProvider session={session}>
          <div className="ws-root min-h-screen lg:flex">
            <SideNav
              pathname={pathname}
              user={session.auth.user}
              onLogout={session.onLogout}
            />
            <main className="min-w-0 flex-1">
              <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 lg:py-12">
                {children}
              </div>
            </main>
            <LearningCompanion />
          </div>
        </AuthSessionProvider>
      )}
    </AuthGate>
  );
}
