"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchSession, login, logout as apiLogout, register, socialLogin } from "@/lib/auth";
import { clearStoredChatSession } from "@/lib/useChat";
import type { AuthToken } from "@/lib/types";
import { getErrorMessage } from "@/lib/apiClient";
import { Workspace } from "./Workspace";
import { BrandMark, NeuronMark } from "./BrandMark";
import { AuthBrandWall } from "./auth/AuthBrandWall";
import { AuthCard, type AuthMode } from "./auth/AuthCard";

type LoginStatus = "checking" | "idle" | "submitting" | "error";

interface AuthGateProps {
  children?: (session: {
    auth: AuthToken;
    onLogout: () => void;
  }) => ReactNode;
}

const NAVY = "hsl(201 100% 13%)";

export function AuthGate({ children }: AuthGateProps) {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthToken | null>(null);
  const [mode, setMode] = useState<AuthMode>("login");
  const [status, setStatus] = useState<LoginStatus>("checking");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("reflexlearn-admin");
  const [registerAccount, setRegisterAccount] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const panelBackground =
    mode === "register"
      ? "bg-[radial-gradient(circle_at_50%_22%,#f4f9ff_0%,#e8f1ff_44%,#dce9f8_100%)]"
      : "bg-[radial-gradient(circle_at_50%_22%,#fff9e8_0%,#f8f0df_42%,#efe7d6_100%)]";

  // 刷新恢复：仅凭 HttpOnly cookie 调 /auth/me，不再读 sessionStorage token。
  useEffect(() => {
    let active = true;
    fetchSession().then((session) => {
      if (!active) return;
      setAuth(session);
      setStatus("idle");
    });
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("submitting");
    setError("");
    try {
      let next: AuthToken;
      if (mode === "register") {
        if (password !== confirmPassword) throw new Error("两次输入的密码不一致");
        next = await register(registerAccount, password);
      } else {
        next = await login(username, password);
      }
      setAuth(next);
      router.replace("/today");
      setStatus("idle");
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setStatus("error");
    }
  }

  async function onSocial(provider: "google" | "github") {
    setStatus("submitting");
    setError("");
    try {
      const next = await socialLogin(provider);
      setAuth(next);
      router.replace("/today");
      setStatus("idle");
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setStatus("error");
    }
  }

  async function logout() {
    await apiLogout();
    clearStoredChatSession();
    setAuth(null);
    setStatus("idle");
  }

  if (status === "checking") {
    return (
      <main
        className="flex min-h-screen flex-col items-center justify-center gap-4 text-sm text-white/60"
        style={{ background: NAVY }}
      >
        <span className="text-white/80">
          <NeuronMark size={40} />
        </span>
        正在恢复会话…
      </main>
    );
  }

  if (auth) {
    if (children) {
      return <>{children({ auth, onLogout: logout })}</>;
    }
    return <Workspace token={auth.access_token} user={auth.user} onLogout={logout} />;
  }

  return (
    <main className="flex min-h-screen" style={{ fontFamily: "var(--font-body)" }}>
      <AuthBrandWall />

      {/* 右侧：暖纸面板，承接手绘卡片材质。 */}
      <div className={`flex flex-1 flex-col transition-colors duration-500 ${panelBackground}`}>
        <div className="p-6 lg:hidden" style={{ color: NAVY }}>
          <BrandMark size={26} />
        </div>

        <div className="flex flex-1 items-center justify-center px-6 pb-16 lg:pb-0">
          <AuthCard
            mode={mode}
            status={status}
            username={username}
            password={password}
            registerAccount={registerAccount}
            confirmPassword={confirmPassword}
            error={error}
            onModeChange={(nextMode) => {
              setMode(nextMode);
              setError("");
              setStatus("idle");
            }}
            onUsernameChange={setUsername}
            onPasswordChange={setPassword}
            onRegisterAccountChange={setRegisterAccount}
            onConfirmPasswordChange={setConfirmPassword}
            onSubmit={onSubmit}
            onSocial={onSocial}
          />
        </div>
      </div>
    </main>
  );
}
