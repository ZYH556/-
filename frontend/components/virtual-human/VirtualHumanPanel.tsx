"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import { AlertCircle, Bot, MessageCircle, PlugZap, Send, Square, X } from "lucide-react";

import { Tag, WsButton } from "@/components/workspace";

type VirtualHumanStatus = "missing" | "sdk-missing" | "ready" | "loading" | "connected" | "failed";

type AvatarPlatform = {
  setApiInfo: (apiInfo: Record<string, unknown>) => AvatarPlatform;
  setGlobalParams: (config: Record<string, unknown>) => AvatarPlatform;
  start: (options?: Record<string, unknown>) => Promise<void>;
  writeText: (text: string, extend?: Record<string, unknown>) => Promise<string>;
  stop: () => void;
  destroy: () => void;
};

type AvatarPlatformConstructor = new (props?: Record<string, unknown>) => AvatarPlatform;

const DEFAULT_SDK_URL = "/avatar-sdk-web/esm/index.js";
const DEFAULT_AVATAR_ID = "201355001";
const DEFAULT_VOICE = "x4_lingxiaoxuan_oral";
const DEFAULT_PROMPT = "同学你好，我是你的 AI 虚拟导师。你可以直接说学习目标，我会帮你规划下一步。";
const QUICK_PROMPTS = [
  "帮我梳理当前薄弱知识点",
  "给我推荐一个短视频",
  "解释一下这道题的思路",
  "帮我规划今天的学习任务",
];

const statusMeta: Record<VirtualHumanStatus, { label: string; tone: "success" | "accent" | "neutral" }> = {
  missing: { label: "待配置", tone: "neutral" },
  "sdk-missing": { label: "缺少 SDK", tone: "neutral" },
  ready: { label: "可连接", tone: "accent" },
  loading: { label: "连接中", tone: "accent" },
  connected: { label: "已连接", tone: "success" },
  failed: { label: "加载失败", tone: "neutral" },
};

export function VirtualHumanPanel() {
  const streamId = useId().replace(/:/g, "");
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<VirtualHumanStatus>("missing");
  const [message, setMessage] = useState(DEFAULT_PROMPT);
  const [error, setError] = useState("");
  const [sdkChecked, setSdkChecked] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);
  const platformRef = useRef<AvatarPlatform | null>(null);
  const startedRef = useRef(false);

  const config = useMemo(
    () => ({
      enabled: process.env.NEXT_PUBLIC_XFYUN_VH_ENABLED?.trim() === "true",
      appId: process.env.NEXT_PUBLIC_XFYUN_VH_APP_ID?.trim() ?? "",
      apiKey: process.env.NEXT_PUBLIC_XFYUN_VH_API_KEY?.trim() ?? "",
      apiSecret: process.env.NEXT_PUBLIC_XFYUN_VH_API_SECRET?.trim() ?? "",
      serviceId: process.env.NEXT_PUBLIC_XFYUN_VH_SERVICE_ID?.trim() ?? "",
      avatarId: process.env.NEXT_PUBLIC_XFYUN_VH_AVATAR_ID?.trim() || DEFAULT_AVATAR_ID,
      vcn: process.env.NEXT_PUBLIC_XFYUN_VH_VCN?.trim() || DEFAULT_VOICE,
      sdkUrl: process.env.NEXT_PUBLIC_XFYUN_VH_SDK_URL?.trim() || DEFAULT_SDK_URL,
    }),
    [],
  );

  const missingItems = [
    !config.enabled ? "启用开关" : "",
    !config.appId ? "APPID" : "",
    !config.apiKey ? "APIKey" : "",
    !config.apiSecret ? "APISecret" : "",
  ].filter(Boolean);
  const blocked = missingItems.length > 0 || status === "sdk-missing";

  useEffect(() => {
    let cancelled = false;

    if (missingItems.length > 0) {
      setSdkChecked(false);
      setStatus("missing");
      return () => {
        cancelled = true;
      };
    }

    if (!config.sdkUrl.startsWith("/")) {
      setSdkChecked(true);
      setStatus("ready");
      return () => {
        cancelled = true;
      };
    }

    setSdkChecked(false);
    fetch(config.sdkUrl, { method: "HEAD", cache: "no-store" })
      .then((response) => {
        if (!cancelled) setStatus(response.ok ? "ready" : "sdk-missing");
      })
      .catch(() => {
        if (!cancelled) setStatus("sdk-missing");
      })
      .finally(() => {
        if (!cancelled) setSdkChecked(true);
      });

    return () => {
      cancelled = true;
    };
  }, [config.sdkUrl, missingItems.length]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        void closeDialog();
      }
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
    // closeDialog is intentionally stable enough for this modal lifecycle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const startVirtualHuman = async () => {
    if (missingItems.length > 0 || status === "sdk-missing" || status === "loading") return;
    const wrapper = streamRef.current;
    if (!wrapper) return;
    setStatus("loading");
    setError("");
    try {
      const sdkModule = (await import(/* webpackIgnore: true */ config.sdkUrl)) as {
        default: AvatarPlatformConstructor;
      };
      const platform = new sdkModule.default({ useInlinePlayer: true });
      platformRef.current = platform;
      platform
        .setApiInfo({
          appId: config.appId,
          apiKey: config.apiKey,
          apiSecret: config.apiSecret,
          sceneId: config.serviceId,
        })
        .setGlobalParams({
          stream: {
            protocol: "xrtc",
            fps: 25,
            bitrate: 1000000,
            alpha: 1,
          },
          avatar: {
            avatar_id: config.avatarId,
            width: 720,
            height: 1280,
            audio_format: 1,
          },
          tts: {
            vcn: config.vcn,
            speed: 50,
            pitch: 50,
            volume: 80,
            audio: {
              sample_rate: 16000,
            },
          },
          avatar_dispatch: {
            interactive_mode: 1,
            enable_action_status: 1,
            content_analysis: 0,
          },
          air: {
            air: 1,
            add_nonsemantic: 1,
          },
        });

      await platform.start({ wrapper });
      startedRef.current = true;
      setStatus("connected");
    } catch (currentError) {
      platformRef.current?.destroy();
      platformRef.current = null;
      startedRef.current = false;
      setStatus("failed");
      setError(currentError instanceof Error ? currentError.message : "虚拟人连接失败");
    }
  };

  useEffect(() => {
    if (!open || blocked || status !== "ready" || startedRef.current) return;
    const timer = window.setTimeout(() => {
      void startVirtualHuman();
    }, 160);
    return () => window.clearTimeout(timer);
    // startVirtualHuman is intentionally omitted so opening the modal triggers one connect attempt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, blocked, status]);

  const stopVirtualHuman = async () => {
    try {
      platformRef.current?.stop();
      platformRef.current?.destroy();
    } finally {
      platformRef.current = null;
      startedRef.current = false;
      setStatus(missingItems.length > 0 ? "missing" : "ready");
    }
  };

  const closeDialog = async () => {
    if (status === "connected" || status === "loading" || status === "failed") {
      await stopVirtualHuman();
    }
    setOpen(false);
  };

  const speak = async () => {
    const text = message.trim();
    if (!text) return;
    if (!startedRef.current) {
      await startVirtualHuman();
    }
    await platformRef.current?.writeText(text, {
      tts: {
        vcn: config.vcn,
        speed: 50,
        pitch: 50,
        volume: 80,
        audio: {
          sample_rate: 16000,
        },
      },
      avatar_dispatch: {
        interactive_mode: 1,
        enable_action_status: 1,
        content_analysis: 0,
      },
      air: {
        air: 1,
        add_nonsemantic: 1,
      },
    });
  };

  const meta = statusMeta[status];

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex h-16 w-16 items-center justify-center rounded-full border border-white/70 bg-[var(--ws-navy)] text-white shadow-[0_14px_34px_rgb(5_26_36/0.24)] transition-transform hover:-translate-y-0.5 hover:shadow-[0_18px_42px_rgb(5_26_36/0.28)] focus:outline-none focus:ring-4 focus:ring-cyan-200"
        aria-label="打开 AI 虚拟导师"
        title="AI 虚拟导师"
      >
        <MessageCircle size={24} aria-hidden />
        <span
          className={`absolute right-1.5 top-1.5 h-3.5 w-3.5 rounded-full border-2 border-white ${
            status === "connected"
              ? "bg-emerald-400"
              : status === "loading"
                ? "bg-cyan-300"
                : blocked || status === "failed"
                  ? "bg-amber-400"
                  : "bg-slate-300"
          }`}
          aria-hidden
        />
      </button>

      {open ? (
        <div
          className="fixed inset-0 z-[80] flex items-center justify-center bg-[rgb(5_26_36/0.42)] px-4 py-6 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="virtual-human-dialog-title"
        >
          <div className="flex max-h-[min(760px,calc(100dvh-48px))] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-white/60 bg-[#fdfcf8] shadow-[0_24px_80px_rgb(5_26_36/0.28)]">
            <header className="flex items-start justify-between gap-4 border-b border-[var(--ws-line)] bg-white px-5 py-4">
              <div className="min-w-0">
                <p className="ws-eyebrow">Virtual Human</p>
                <h2 id="virtual-human-dialog-title" className="mt-1 text-lg font-medium text-[var(--ws-ink)]">
                  AI 虚拟导师
                </h2>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Tag tone={meta.tone}>{meta.label}</Tag>
                <button
                  type="button"
                  onClick={() => void closeDialog()}
                  className="flex h-10 w-10 items-center justify-center rounded-xl border border-[var(--ws-line)] bg-[#fbfaf7] text-slate-500 transition-colors hover:border-[var(--ws-line-strong)] hover:text-[var(--ws-ink)]"
                  aria-label="关闭虚拟导师弹窗"
                >
                  <X size={18} aria-hidden />
                </button>
              </div>
            </header>

            <div className="grid min-h-0 flex-1 gap-0 overflow-y-auto lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="bg-[#f5f2ea] p-4 sm:p-5">
                <div
                  ref={streamRef}
                  id={streamId}
                  className="flex h-[min(560px,58dvh)] min-h-[360px] items-center justify-center overflow-hidden border border-[var(--ws-line)] bg-black"
                  aria-label="虚拟人视频区域"
                >
                  {status === "connected" ? null : (
                    <div className="flex max-w-[240px] flex-col items-center px-5 text-center">
                      <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-white text-[var(--ws-accent)] shadow-[0_1px_2px_rgb(5_26_36/0.06)]">
                        <Bot size={22} aria-hidden />
                      </span>
                      <p className="mt-4 text-sm font-medium text-white">
                        {status === "loading" ? "正在连接虚拟导师" : "虚拟导师等待连接"}
                      </p>
                      <p className="mt-2 text-xs leading-5 text-white/65">
                        {status === "failed" ? "连接失败后可重新尝试。" : "连接后将在这里显示虚拟导师。"}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              <aside className="flex min-h-0 flex-col border-t border-[var(--ws-line)] bg-white p-5 lg:border-l lg:border-t-0">
                <div className="grid gap-2 text-xs text-slate-500">
                  <div className="flex items-center justify-between border border-[var(--ws-line)] bg-[#fbfaf7] px-3 py-2">
                    <span>接口服务</span>
                    <span className="max-w-[170px] truncate text-[var(--ws-ink)]">{config.serviceId || "未填写"}</span>
                  </div>
                  <div className="flex items-center justify-between border border-[var(--ws-line)] bg-[#fbfaf7] px-3 py-2">
                    <span>虚拟形象</span>
                    <span className="text-[var(--ws-ink)]">{config.avatarId}</span>
                  </div>
                </div>

                {error ? (
                  <div className="mt-4 flex gap-2 border border-rose-200 bg-rose-50 p-3 text-xs leading-5 text-rose-700">
                    <AlertCircle className="mt-0.5 shrink-0" size={14} aria-hidden />
                    <p>{error}</p>
                  </div>
                ) : null}

                {blocked ? (
                  <div className="mt-4 flex gap-2 border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-700">
                    <AlertCircle className="mt-0.5 shrink-0" size={14} aria-hidden />
                    <p>
                      {missingItems.length > 0
                        ? `还缺少：${missingItems.join("、")}`
                        : "SDK 文件未找到"}
                    </p>
                  </div>
                ) : (
                  <div className="mt-4 flex items-center gap-2 border border-[var(--ws-line)] bg-[#fbfaf7] px-3 py-2 text-xs text-slate-500">
                    {status === "loading" ? <PlugZap size={14} aria-hidden /> : <Bot size={14} aria-hidden />}
                    <span>
                      {status === "loading"
                        ? "正在自动连接虚拟导师"
                        : status === "connected"
                          ? "虚拟导师已在线"
                          : "打开弹窗后会自动连接"}
                    </span>
                  </div>
                )}

                <div className="mt-4 flex gap-2">
                  <WsButton
                    variant="outline"
                    onClick={stopVirtualHuman}
                    disabled={status !== "connected"}
                    className="min-h-10 flex-1 justify-center"
                  >
                    <Square size={14} aria-hidden />
                    停止
                  </WsButton>
                  <WsButton
                    variant="outline"
                    onClick={() => void closeDialog()}
                    className="min-h-10 flex-1 justify-center"
                  >
                    <X size={14} aria-hidden />
                    收起
                  </WsButton>
                </div>

                <div className="mt-5">
                  <p className="text-xs font-medium text-[var(--ws-ink)]">快捷提问</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {QUICK_PROMPTS.map((prompt) => (
                      <button
                        key={prompt}
                        type="button"
                        onClick={() => setMessage(prompt)}
                        className="min-h-9 rounded-full border border-[var(--ws-line)] bg-[#fbfaf7] px-3 text-xs text-slate-600 transition-colors hover:border-[var(--ws-accent)] hover:text-[var(--ws-ink)]"
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-auto pt-5">
                  <label htmlFor="virtual-human-speak" className="text-xs font-medium text-[var(--ws-ink)]">
                    虚拟导师播报
                  </label>
                  <textarea
                    id="virtual-human-speak"
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    rows={4}
                    className="mt-2 w-full resize-none border border-[var(--ws-line-strong)] bg-white px-3 py-2 text-sm leading-6 text-[var(--ws-ink)] outline-none transition-colors placeholder:text-slate-400 focus:border-[var(--ws-accent)]"
                    placeholder="输入要让虚拟导师播报的话"
                  />
                  <WsButton
                    variant="primary"
                    onClick={speak}
                    disabled={blocked || !message.trim() || status === "loading"}
                    className="mt-3 min-h-11 w-full justify-center"
                  >
                    <Send size={15} aria-hidden />
                    让虚拟导师讲解
                  </WsButton>
                </div>
              </aside>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
