from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel

from reflexlearn.common.config import get_settings


class Completion(BaseModel):
    text: str
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


# 低价值 / 高频任务走便宜档模型（docs §2「按价值分级管理上下文」的成本感知路由）。
CHEAP_TASK_TYPES = {"summary"}


class LLMGateway:
    def __init__(self):
        self._settings = get_settings()

    async def complete(
        self,
        messages: list[dict],
        *,
        task_type: str = "generation",
        schema: Optional[type[BaseModel]] = None,
        temperature: float = 0.7,
    ) -> Completion:
        model = self._select_model(task_type)
        api_key = self._get_api_key(model)
        if not api_key:
            # 未配置任何 LLM 凭证：绝不发起外呼（受限网络下会挂起到超时），
            # 立即抛错，交由上层 Skill / 节点走本地 fallback（离线占位、规则规划等）。
            raise RuntimeError("llm_no_api_key")

        import litellm

        start = time.time()
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if api_key:
            kwargs["api_key"] = api_key
        if schema:
            kwargs["response_format"] = {"type": "json_object"}

        resp = await litellm.acompletion(**kwargs)
        latency = int((time.time() - start) * 1000)

        content = resp.choices[0].message.content or ""
        usage = resp.usage
        return Completion(
            text=content,
            model_used=model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cost_usd=0.0,
            latency_ms=latency,
        )

    def _select_model(self, task_type: str) -> str:
        s = self._settings
        cheap = task_type in CHEAP_TASK_TYPES
        # 低价值任务（如 summary）成本感知路由：显式覆盖优先，否则按 provider 选便宜/快档。
        # 非低价值任务的选型与改造前逐字节一致（零回归）。
        if cheap and s.summary_model:
            return s.summary_model
        if s.deepseek_api_key:
            return "deepseek/deepseek-chat"  # deepseek-chat 已是便宜档，无更低档
        if s.qwen_api_key:
            return "openai/qwen-turbo" if cheap else "openai/qwen-plus"
        if s.anthropic_api_key:
            return "anthropic/claude-haiku-4-5" if cheap else "anthropic/claude-sonnet-4-6"
        return "deepseek/deepseek-chat"

    def _get_api_key(self, model: str) -> str:
        s = self._settings
        if "deepseek" in model:
            return s.deepseek_api_key
        if "qwen" in model:
            return s.qwen_api_key
        if "anthropic" in model or "claude" in model:
            return s.anthropic_api_key
        return ""
