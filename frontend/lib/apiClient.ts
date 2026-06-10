export function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "请求失败";
}

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);
const CSRF_COOKIE = "reflexlearn_csrf";

// double-submit：从非 HttpOnly 的 csrf cookie 读 token，写请求放入 X-CSRF-Token 头。
export function readCsrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${CSRF_COOKIE}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : "";
}

export async function authFetch(
  url: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  // 会话凭证以 HttpOnly cookie 为准（credentials: "include"）；
  // token 仅在开发/脚本场景作为 Bearer 兼容，空串时不附加。
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const method = (init.method ?? "GET").toUpperCase();
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  return fetch(url, { ...init, headers, credentials: "include" });
}

export async function apiJson<T>(
  url: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const resp = await authFetch(url, token, { ...init, headers });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as T;
}

export async function apiForm<T>(
  url: string,
  token: string,
  body: FormData,
): Promise<T> {
  const resp = await authFetch(url, token, { method: "POST", body });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as T;
}
