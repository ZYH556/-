import type { SSEMessage } from "./types";
import { readCsrfToken } from "./apiClient";

/**
 * 解析后端的 POST + text/event-stream 响应。
 * 浏览器原生 EventSource 仅支持 GET，故这里用 fetch + ReadableStream 手动解析。
 * 每个 SSE 消息块以空行（\n\n）分隔，块内 `event:` / `data:` 行分别给出事件名与负载。
 */
export async function* parseSSEStream(
  url: string,
  body: unknown,
  signal: AbortSignal,
  token: string,
): AsyncGenerator<SSEMessage> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  // 会话凭证以 HttpOnly cookie 为准（credentials: "include"）；
  // token 空串时不附加 Bearer（仅开发/脚本兼容）。
  if (token) headers.Authorization = `Bearer ${token}`;
  // cookie 会话下写请求需带 CSRF（double-submit）。
  const csrf = readCsrfToken();
  if (csrf) headers["X-CSRF-Token"] = csrf;
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal,
    credentials: "include",
  });

  if (!res.ok || !res.body) {
    throw new Error(`请求失败：HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? ""; // 末块可能不完整，留到下一轮拼接

    for (const block of blocks) {
      const msg = parseBlock(block);
      if (msg) yield msg;
    }
  }

  const tail = parseBlock(buffer);
  if (tail) yield tail;
}

function parseBlock(block: string): SSEMessage | null {
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try {
    return { event, data: JSON.parse(data) };
  } catch {
    return null;
  }
}
