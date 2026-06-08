"""L1 上下文工程 · TrimStrategy（无状态纯函数）。

docs §2.2/§2.3 的三层上下文控制落地：固定锚点 + 滑动窗口 + 语义重要性 + summary buffer 注入。

关键设计（计划「三条不可违背约束」）：
- 纯函数无状态：输入 messages/summary_context → 输出精简 messages，不修改入参、不持有可变
  状态（MemoryManager 单例安全，杜绝跨 session 串台）。
- 结果仅供「LLM 调用前临时构造上下文」，绝不回写 state["messages"]（messages 是 add_messages
  reducer，回写只追加）。
- 兼容 dict 与 LangChain BaseMessage（add_messages 会把 dict 转成 BaseMessage 对象）：
  统一规范化为 {role, content} dict 输出，调用方可安全 json.dumps。
"""
from __future__ import annotations

from dataclasses import dataclass

from reflexlearn.common.config import get_settings

# 语义重要性标记：含这些关键词/角色的轮次视为高价值，优先保留
_IMPORTANT_KEYWORDS = (
    "tool_call", "plan", "verify", "reflection",
    "失败", "错误", "重要", "工具", "决策", "结论",
)
_IMPORTANT_ROLES = {"tool", "function"}
# LangChain message.type → 通用 role
_ROLE_MAP = {"human": "user", "ai": "assistant"}


@dataclass
class TrimConfig:
    recent_turns: int = 6        # 最近 N 轮原文完整保留
    max_chars: int = 6000        # 总字符预算（中文友好，避免引 tiktoken）
    anchor_roles: tuple = ("system",)

    @classmethod
    def from_settings(cls) -> "TrimConfig":
        try:
            s = get_settings()
            return cls(
                recent_turns=getattr(s, "summary_recent_turns", 6),
                max_chars=getattr(s, "context_max_chars", 6000),
            )
        except Exception:
            return cls()


def _normalize(m) -> dict:
    """dict 或 LangChain BaseMessage → {role, content} dict（幂等）。"""
    if isinstance(m, dict):
        return {
            "role": m.get("role", "user") or "user",
            "content": str(m.get("content", "") or ""),
        }
    role = getattr(m, "type", None) or getattr(m, "role", None) or "user"
    return {
        "role": _ROLE_MAP.get(role, role),
        "content": str(getattr(m, "content", "") or ""),
    }


def estimate_len(messages) -> int:
    return sum(len(_normalize(m)["content"]) for m in (messages or []))


def is_important(msg) -> bool:
    m = _normalize(msg)
    if m["role"] in _IMPORTANT_ROLES:
        return True
    low = m["content"].lower()
    return any(k.lower() in low for k in _IMPORTANT_KEYWORDS)


def trim_context(messages, summary_context: str = "", config: TrimConfig | None = None) -> list[dict]:
    """纯函数。返回精简后的 messages（规范化 dict，不修改入参）。

    ① system 锚点原样置顶；
    ② 有 summary_context → 插一条 system 历史摘要（在锚点后）；
    ③ 最近 recent_turns 轮原文保留；
    ④ 中段命中 is_important 的轮次择优保留至 max_chars 预算；
    ⑤ 输入本就很短（无中段且无摘要）→ 原样返回（不丢轮次）。
    """
    config = config or TrimConfig.from_settings()
    msgs = [_normalize(m) for m in (messages or [])]

    anchors = [m for m in msgs if m["role"] in config.anchor_roles]
    non_anchor = [m for m in msgs if m["role"] not in config.anchor_roles]

    recent_count = max(config.recent_turns * 2, 0)  # user+assistant 成对
    recent = non_anchor[-recent_count:] if recent_count else []
    middle = non_anchor[:-recent_count] if recent_count else non_anchor

    summary_msgs: list[dict] = []
    if summary_context:
        summary_msgs = [{"role": "system", "content": f"[历史摘要]\n{summary_context}"}]

    # 短输入直返：无中段（历史未超窗口）且无摘要 → 原样返回，不丢轮次
    if not middle and not summary_msgs:
        return anchors + recent

    # 中段：按语义重要性保留，受字符预算约束
    important = [m for m in middle if is_important(m)]
    budget = config.max_chars - estimate_len(anchors + summary_msgs + recent)
    kept: list[dict] = []
    for m in important:
        c = len(m["content"])
        if budget - c < 0:
            break
        kept.append(m)
        budget -= c

    return anchors + summary_msgs + kept + recent
