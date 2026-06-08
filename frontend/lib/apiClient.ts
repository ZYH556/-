export function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "请求失败";
}

export async function authFetch(
  url: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...init, headers });
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
