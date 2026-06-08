import type { AuthToken, CurrentUser } from "./types";

const AUTH_KEY = "reflexlearn_auth";

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

function isAuthToken(value: unknown): value is AuthToken {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.access_token === "string" &&
    typeof v.token_type === "string" &&
    typeof v.expires_in === "number" &&
    isCurrentUser(v.user)
  );
}

export function getStoredAuth(): AuthToken | null {
  if (typeof window === "undefined") return null;
  const raw = window.sessionStorage.getItem(AUTH_KEY);
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    return isAuthToken(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function storeAuth(auth: AuthToken): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}

export function clearAuth(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(AUTH_KEY);
}

export async function login(username: string, password: string): Promise<AuthToken> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    throw new Error(resp.status === 401 ? "账号或密码错误" : `登录失败：HTTP ${resp.status}`);
  }
  const body: unknown = await resp.json();
  if (!isAuthToken(body)) throw new Error("登录响应格式不正确");
  storeAuth(body);
  return body;
}
