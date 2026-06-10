"use client";

import { FormEvent, ReactNode, useEffect, useState } from "react";
import { fetchSession, login, logout as apiLogout } from "@/lib/auth";
import { clearStoredChatSession } from "@/lib/useChat";
import type { AuthToken } from "@/lib/types";
import { getErrorMessage } from "@/lib/apiClient";
import { Workspace } from "./Workspace";
import { BrandMark, NeuronMark } from "./BrandMark";

type LoginStatus = "checking" | "idle" | "submitting" | "error";

interface AuthGateProps {
  children?: (session: {
    auth: AuthToken;
    onLogout: () => void;
  }) => ReactNode;
}

const HIGHLIGHTS = [
  "协作全过程可见——从画像、规划到学习路径，每一步都有理由。",
  "三路混合检索——语义、关键词与知识图谱，回答有出处。",
  "越用越懂你——每一次对话，都在沉淀为你的专属经验。",
];

const NAVY = "hsl(201 100% 13%)";

/** 左侧品牌墙：夜空视频 + 衬线主张 + 亮点轮播。 */
function BrandWall() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % HIGHLIGHTS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="relative hidden overflow-hidden text-white lg:flex lg:w-[55%] lg:flex-col lg:justify-between">
      <video
        className="absolute inset-0 h-full w-full object-cover"
        src="/hero-loop.mp4"
        autoPlay
        loop
        muted
        playsInline
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(135deg, rgba(0,30,46,0.55) 0%, rgba(0,30,46,0.15) 55%, rgba(0,30,46,0.6) 100%)",
        }}
      />

      <div className="relative p-10">
        <BrandMark size={30} />
      </div>

      <div className="relative p-10 pb-12">
        <h2
          className="max-w-md text-4xl leading-[1.25]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          六个智能体，
          <br />
          为你协作。
        </h2>
        <div className="mt-8 h-14 max-w-md">
          {HIGHLIGHTS.map((text, i) => (
            <p
              key={text}
              className="absolute max-w-md text-sm leading-relaxed text-white/80 transition-opacity duration-700"
              style={{ opacity: i === index ? 1 : 0 }}
            >
              ✦ {text}
            </p>
          ))}
        </div>
        <div className="mt-6 flex gap-2">
          {HIGHLIGHTS.map((_, i) => (
            <span
              key={i}
              className="h-1 rounded-full transition-all duration-500"
              style={{
                width: i === index ? 24 : 10,
                background: i === index ? "#7dd3fc" : "rgba(255,255,255,0.3)",
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function AuthGate({ children }: AuthGateProps) {
  const [auth, setAuth] = useState<AuthToken | null>(null);
  const [status, setStatus] = useState<LoginStatus>("checking");
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("reflexlearn-admin");
  const [error, setError] = useState("");

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
      const next = await login(username, password);
      setAuth(next);
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

  const inputClass =
    "mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 transition-colors focus:border-cyan-600 focus:outline-none focus:ring-2 focus:ring-cyan-600/15";

  return (
    <main className="flex min-h-screen" style={{ fontFamily: "var(--font-body)" }}>
      <BrandWall />

      {/* 右侧：暖白表单面板（与主页白色内容面板同材质） */}
      <div className="flex flex-1 flex-col bg-[#f7f5f0]">
        <div className="p-6 lg:hidden" style={{ color: NAVY }}>
          <BrandMark size={26} />
        </div>

        <div className="flex flex-1 items-center justify-center px-6 pb-16 lg:pb-0">
          <section className="w-full max-w-sm">
            <h1
              className="text-3xl"
              style={{ fontFamily: "var(--font-display)", color: NAVY }}
            >
              欢迎回来
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              登录后进入多智能体学习工作台
            </p>

            <form onSubmit={onSubmit} className="mt-8 space-y-4">
              <label className="block text-sm font-medium text-slate-700">
                账号
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className={inputClass}
                  autoComplete="username"
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                密码
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  className={inputClass}
                  autoComplete="current-password"
                />
              </label>
              {status === "error" && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-sm text-rose-700">
                  {error}
                </div>
              )}
              <button
                type="submit"
                disabled={status === "submitting"}
                className="w-full rounded-xl px-3.5 py-3 text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
                style={{ background: NAVY }}
              >
                {status === "submitting" ? "登录中…" : "进入工作台"}
              </button>
            </form>

            <p className="mt-6 text-xs leading-relaxed text-slate-400">
              开发环境默认账号已预填，生产环境请使用租户分配的账号登录。
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
