import type { AuthToken, CurrentUser } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";

function isCurrentUser(value: unknown): value is CurrentUser {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.user_id === "string" &&
    typeof v.tenant_id === "string" &&
    typeof v.role === "string"
  );
}

interface LoginResponse {
  user: CurrentUser;
  token_type?: string;
  expires_in?: number;
  access_token?: string | null;
}

function isLoginResponse(value: unknown): value is LoginResponse {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return isCurrentUser(v.user);
}

function toAuthToken(body: LoginResponse): AuthToken {
  return {
    access_token: typeof body.access_token === "string" ? body.access_token : "",
    token_type: body.token_type ?? "bearer",
    expires_in: typeof body.expires_in === "number" ? body.expires_in : 0,
    user: body.user,
  };
}

export async function login(username: string, password: string): Promise<AuthToken> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    throw new Error(resp.status === 401 ? "账号或密码错误" : `登录失败：HTTP ${resp.status}`);
  }
  const body: unknown = await resp.json();
  if (!isLoginResponse(body)) throw new Error("登录响应格式不正确");
  return toAuthToken(body);
}

// 刷新恢复：仅凭 HttpOnly cookie 调 /auth/me，token 不再持久化到 sessionStorage。
export async function fetchSession(): Promise<AuthToken | null> {
  try {
    const resp = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
    if (!resp.ok) return null;
    const user: unknown = await resp.json();
    if (!isCurrentUser(user)) return null;
    return { access_token: "", token_type: "bearer", expires_in: 0, user };
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" });
  } catch {
    // best-effort：cookie 清理失败不应阻断前端登出
  }
}
