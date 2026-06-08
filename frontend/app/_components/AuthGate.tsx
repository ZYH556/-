"use client";

import { FormEvent, useEffect, useState } from "react";
import { clearAuth, getStoredAuth, login } from "@/lib/auth";
import type { AuthToken } from "@/lib/types";
import { getErrorMessage } from "@/lib/apiClient";
import { Workspace } from "./Workspace";

type LoginStatus = "checking" | "idle" | "submitting" | "error";

export function AuthGate() {
  const [auth, setAuth] = useState<AuthToken | null>(null);
  const [status, setStatus] = useState<LoginStatus>("checking");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("reflexlearn-admin");
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = getStoredAuth();
    setAuth(stored);
    setStatus("idle");
  }, []);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setStatus("submitting");
    setError("");
    try {
      const next = await login(username, password);
      setAuth(next);
      setStatus("idle");
    } catch (err: unknown) {
      setError(getErrorMessage(err));
      setStatus("error");
    }
  }

  function logout() {
    clearAuth();
    setAuth(null);
    setStatus("idle");
  }

  if (auth) {
    return <Workspace token={auth.access_token} user={auth.user} onLogout={logout} />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <section className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5">
          <h1 className="text-xl font-semibold text-slate-900">ReflexLearn</h1>
          <p className="mt-1 text-sm text-slate-500">登录后进入多智能体学习工作台</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="block text-sm font-medium text-slate-700">
            账号
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              autoComplete="username"
            />
          </label>
          <label className="block text-sm font-medium text-slate-700">
            密码
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              autoComplete="current-password"
            />
          </label>
          {status === "error" && (
            <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={status === "submitting"}
            className="w-full rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:opacity-50"
          >
            {status === "submitting" ? "登录中..." : "登录"}
          </button>
        </form>
      </section>
    </main>
  );
}
