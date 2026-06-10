"use client";

import { createContext, ReactNode, useContext } from "react";
import type { AuthToken } from "./types";

interface AuthSession {
  auth: AuthToken;
  onLogout: () => void;
}

const AuthSessionContext = createContext<AuthSession | null>(null);

export function AuthSessionProvider({
  session,
  children,
}: {
  session: AuthSession;
  children: ReactNode;
}) {
  return <AuthSessionContext.Provider value={session}>{children}</AuthSessionContext.Provider>;
}

export function useAuthSession(): AuthSession {
  const session = useContext(AuthSessionContext);
  if (!session) {
    throw new Error("AuthSessionProvider missing");
  }
  return session;
}
