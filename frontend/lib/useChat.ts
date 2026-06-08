"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { parseSSEStream } from "./sse";
import type {
  AgentStep,
  DebateRound,
  JudgeVerdict,
  LearningPath,
  ResourceCard,
} from "./types";

export type ChatStatus = "idle" | "streaming" | "done" | "error";

const SID_KEY = "reflexlearn_sid";

export interface Turn {
  id: number;
  userMessage: string;
  status: ChatStatus;
  steps: AgentStep[];
  cards: Map<string, ResourceCard>;
  debateRounds: DebateRound[];
  verdict: JudgeVerdict | null;
  path: LearningPath | null;
  error: string | null;
}

type Action =
  | { type: "start"; message: string }
  | { type: "agent_step"; payload: AgentStep }
  | { type: "resource_card"; payload: ResourceCard }
  | { type: "debate_round"; payload: DebateRound }
  | { type: "judge_verdict"; payload: JudgeVerdict }
  | { type: "learning_path"; payload: LearningPath }
  | { type: "done" }
  | { type: "error"; payload: string }
  | { type: "reset" };

function newTurn(id: number, message: string): Turn {
  return {
    id,
    userMessage: message,
    status: "streaming",
    steps: [],
    cards: new Map(),
    debateRounds: [],
    verdict: null,
    path: null,
    error: null,
  };
}

// 多轮累积：每次仅更新最后一个 turn（当前进行中的轮次），历史 turn 不可变保留
function updateLast(turns: Turn[], fn: (t: Turn) => Turn): Turn[] {
  if (turns.length === 0) return turns;
  const copy = turns.slice();
  copy[copy.length - 1] = fn(copy[copy.length - 1]);
  return copy;
}

function reducer(turns: Turn[], action: Action): Turn[] {
  switch (action.type) {
    case "start":
      return [...turns, newTurn(turns.length, action.message)];
    case "agent_step":
      return updateLast(turns, (t) => ({ ...t, steps: [...t.steps, action.payload] }));
    case "resource_card":
      return updateLast(turns, (t) => {
        const cards = new Map(t.cards);
        // 生成阶段与 assemble 阶段会重复 emit 同一卡片，按 task_id 去重（后到的更完整、覆盖前者）
        const key = action.payload.task_id || `card-${cards.size}`;
        cards.set(key, action.payload);
        return { ...t, cards };
      });
    case "debate_round":
      return updateLast(turns, (t) => ({
        ...t,
        debateRounds: [...t.debateRounds, action.payload],
      }));
    case "judge_verdict":
      return updateLast(turns, (t) => ({ ...t, verdict: action.payload }));
    case "learning_path":
      return updateLast(turns, (t) => ({ ...t, path: action.payload }));
    case "done":
      return updateLast(turns, (t) => (t.status === "error" ? t : { ...t, status: "done" }));
    case "error":
      return updateLast(turns, (t) => ({ ...t, status: "error", error: action.payload }));
    case "reset":
      return [];
    default:
      return turns;
  }
}

function getErrorMessage(e: unknown): string {
  return e instanceof Error ? e.message : "连接出错";
}

function isAbortError(e: unknown): boolean {
  return e instanceof DOMException
    ? e.name === "AbortError"
    : e instanceof Error && e.name === "AbortError";
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function getStoredChatSession(): string {
  if (typeof window === "undefined") return "";
  window.localStorage.removeItem(SID_KEY);
  return window.sessionStorage.getItem(SID_KEY) || "";
}

function storeChatSession(sessionId: string): void {
  if (typeof window === "undefined" || !sessionId) return;
  window.sessionStorage.setItem(SID_KEY, sessionId);
}

export function clearStoredChatSession(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(SID_KEY);
  window.localStorage.removeItem(SID_KEY);
}

export function useChat(token: string) {
  const [turns, dispatch] = useReducer(reducer, []);
  const abortRef = useRef<AbortController | null>(null);
  const sessionRef = useRef<string>("");

  // 初始化：只从当前浏览器会话恢复 sid，避免登出/换号后跨账号沿用。
  useEffect(() => {
    sessionRef.current = getStoredChatSession();
  }, []);

  const send = useCallback(async (message: string) => {
    if (!message.trim()) return;
    abortRef.current?.abort(); // 取消上一次未完成的流，避免事件串台
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    dispatch({ type: "start", message });

    const base = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api";
    let errored = false;
    try {
      for await (const msg of parseSSEStream(
        `${base}/chat`,
        { message, session_id: sessionRef.current },
        ctrl.signal,
        token,
      )) {
        switch (msg.event) {
          case "session": {
            // 首帧回传 session_id：存 ref + sessionStorage，下一轮带回延续多轮
            const data = asRecord(msg.data);
            sessionRef.current = asString(data.session_id) || sessionRef.current;
            storeChatSession(sessionRef.current);
            break;
          }
          case "agent_step":
            dispatch({ type: "agent_step", payload: msg.data as AgentStep });
            break;
          case "resource_card":
            dispatch({ type: "resource_card", payload: msg.data as ResourceCard });
            break;
          case "debate_round":
            dispatch({ type: "debate_round", payload: msg.data as DebateRound });
            break;
          case "judge_verdict":
            dispatch({ type: "judge_verdict", payload: msg.data as JudgeVerdict });
            break;
          case "learning_path":
            dispatch({ type: "learning_path", payload: msg.data as LearningPath });
            break;
          case "error": {
            const data = asRecord(msg.data);
            errored = true;
            dispatch({ type: "error", payload: asString(data.error) || "服务端出错" });
            break;
          }
          case "done":
            dispatch({ type: "done" });
            break;
        }
      }
      if (!errored) dispatch({ type: "done" }); // 流自然结束但未显式 done 时兜底
    } catch (e: unknown) {
      if (!isAbortError(e)) {
        dispatch({ type: "error", payload: getErrorMessage(e) });
      }
    }
  }, [token]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: "done" });
  }, []);

  // 新会话：中断当前流、清空历史 turns、丢弃 session_id（后端下次生成新 sid）
  const resetSession = useCallback(() => {
    abortRef.current?.abort();
    sessionRef.current = "";
    clearStoredChatSession();
    dispatch({ type: "reset" });
  }, []);

  const streaming =
    turns.length > 0 && turns[turns.length - 1].status === "streaming";

  return { turns, send, stop, resetSession, streaming };
}
