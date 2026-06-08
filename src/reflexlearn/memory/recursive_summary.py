"""L1 上下文工程 · 递归摘要 buffer（无状态纯函数）。

docs §2.4 的递归摘要落地，但 layers 不放实例属性（计划「三条不可违背约束」#1）：
layers 作为参数传入/传出，随 session 存 Redis，MemoryManager 单例不持有可变状态。

降级（铁律）：LLM 为 None / 抛 llm_no_api_key / 任何异常 → 规则截断，绝不报错中断。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from reflexlearn.common.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    max_layer_chars: int = 800
    max_depth: int = 3

    @classmethod
    def from_settings(cls) -> "SummaryConfig":
        try:
            s = get_settings()
            return cls(
                max_layer_chars=getattr(s, "summary_max_layer_chars", 800),
                max_depth=getattr(s, "summary_max_depth", 3),
            )
        except Exception:
            return cls()


def get_context(layers) -> str:
    """把摘要层拼成注入 prompt 的文本。空 → ''。"""
    return "\n---\n".join(s for s in (layers or []) if s)


def _messages_to_text(messages) -> str:
    parts = []
    for m in messages or []:
        if isinstance(m, dict):
            role, content = m.get("role", ""), str(m.get("content", "") or "")
        else:
            role = getattr(m, "type", None) or getattr(m, "role", "")
            content = str(getattr(m, "content", "") or "")
        if content:
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _rule_truncate(messages, max_chars: int) -> str:
    """LLM 不可用时的降级摘要：取对话末段拼成一句离线摘要（绝不报错）。"""
    text = _messages_to_text(messages)
    if not text:
        return ""
    return f"（离线摘要）最近讨论：{text[-max_chars:]}"


async def add_and_compress(layers, new_messages, llm, config: SummaryConfig | None = None) -> list[str]:
    """把被挤出窗口的 new_messages 压缩进 layers，返回新 layers（纯函数，不改入参）。

    - llm 可用 → complete(task_type='summary') 生成本层摘要；
    - llm 为 None / 抛 llm_no_api_key / 任何异常 → 规则截断降级；
    - 压缩后层数超 max_depth → 合并最老两层。
    """
    config = config or SummaryConfig.from_settings()
    layers = list(layers or [])
    new_messages = list(new_messages or [])
    if not new_messages:
        return layers

    summary = await _summarize(new_messages, llm, config)
    if not summary:
        return layers
    layers.append(summary)

    while len(layers) > config.max_depth and len(layers) > 1:
        layers = await _merge(layers, llm, config)
    return layers


async def _summarize(messages, llm, config: SummaryConfig) -> str:
    if llm is None:
        return _rule_truncate(messages, config.max_layer_chars)
    try:
        resp = await llm.complete(
            [
                {"role": "system", "content": "将以下对话历史压缩为简洁摘要，保留关键决策、结论和失败教训，删除重复和无实质内容，控制在 200 字以内。"},
                {"role": "user", "content": _messages_to_text(messages)},
            ],
            task_type="summary",
            temperature=0.3,
        )
        return (resp.text or "").strip() or _rule_truncate(messages, config.max_layer_chars)
    except Exception as e:
        logger.info("recursive_summary degraded to rule truncate: %s", e)
        return _rule_truncate(messages, config.max_layer_chars)


async def _merge(layers, llm, config: SummaryConfig) -> list[str]:
    """合并最老两层为一层（LLM 不可用则字符串拼接降级）。返回新 layers。"""
    older, newer = layers[0], layers[1]
    merged = None
    if llm is not None:
        try:
            resp = await llm.complete(
                [
                    {"role": "system", "content": "合并以下两段摘要为一段更精炼的摘要，保留关键信息，控制在 200 字以内。"},
                    {"role": "user", "content": f"旧摘要:\n{older}\n\n新摘要:\n{newer}"},
                ],
                task_type="summary",
                temperature=0.3,
            )
            merged = (resp.text or "").strip() or None
        except Exception as e:
            logger.info("recursive_summary merge degraded: %s", e)
    if not merged:
        merged = f"{older} / {newer}"
    return [merged] + layers[2:]
