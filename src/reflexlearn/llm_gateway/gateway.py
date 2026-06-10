from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel

from reflexlearn.common.config import get_settings
from reflexlearn.llm_gateway import openai_compat
from reflexlearn.observability.metrics import observe_degradation, observe_llm


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
        if task_type == "generation" and not self._settings.enable_llm_generation:
            observe_degradation("llm", "generation_disabled")
            raise RuntimeError("generation_disabled_no_api_key")
        model = self._select_model(task_type)
        api_key = self._get_api_key(model)
        if not api_key:
            # 未配置任何 LLM 凭证：绝不发起外呼（受限网络下会挂起到超时），
            # 立即抛错，交由上层 Skill / 节点走本地 fallback（离线占位、规则规划等）。
            observe_llm(
                task_type=task_type,
                model=model,
                status="no_key",
                latency_ms=0,
            )
            observe_degradation("llm", "no_api_key")
            raise RuntimeError("llm_no_api_key")

        if self._is_openai_compat_model(model):
            return await self._complete_openai_compat(
                model=model,
                messages=messages,
                task_type=task_type,
                schema=schema,
                temperature=temperature,
            )

        import litellm

        start = time.time()
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "timeout": self._settings.llm_request_timeout_s,
        }
        if api_key:
            kwargs["api_key"] = api_key
        api_base = self._api_base_for_model(model)
        if api_base:
            kwargs["api_base"] = api_base
        if schema:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = await litellm.acompletion(**kwargs)
            latency = int((time.time() - start) * 1000)

            content = resp.choices[0].message.content or ""
            usage = resp.usage
            completion = Completion(
                text=content,
                model_used=model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                cost_usd=0.0,
                latency_ms=latency,
            )
            observe_llm(
                task_type=task_type,
                model=model,
                status="ok",
                latency_ms=latency,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
            return completion
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            observe_llm(
                task_type=task_type,
                model=model,
                status="error",
                latency_ms=latency,
            )
            observe_degradation("llm", type(e).__name__)
            raise

    async def _complete_openai_compat(
        self,
        *,
        model: str,
        messages: list[dict],
        task_type: str,
        schema: Optional[type[BaseModel]],
        temperature: float,
    ) -> Completion:
        import httpx

        start = time.time()
        wire_api = openai_compat.wire_api(self._settings)
        payload = openai_compat.payload(
            self._settings,
            messages=messages,
            schema=schema,
            temperature=temperature,
            api=wire_api,
        )
        headers = {
            "Authorization": f"Bearer {self._settings.openai_compat_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._settings.llm_request_timeout_s) as client:
                resp = await client.post(
                    openai_compat.request_url(self._settings, wire_api),
                    headers=headers,
                    json=payload,
                )
            resp.raise_for_status()
            data = resp.json()
            latency = int((time.time() - start) * 1000)
            input_tokens, output_tokens = openai_compat.usage_tokens(data, wire_api)
            completion = Completion(
                text=openai_compat.response_text(data, wire_api),
                model_used=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=0.0,
                latency_ms=latency,
            )
            observe_llm(
                task_type=task_type,
                model=model,
                status="ok",
                latency_ms=latency,
                input_tokens=completion.input_tokens,
                output_tokens=completion.output_tokens,
            )
            return completion
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            observe_llm(
                task_type=task_type,
                model=model,
                status="error",
                latency_ms=latency,
            )
            observe_degradation("llm", type(e).__name__)
            raise

    def _select_model(self, task_type: str) -> str:
        s = self._settings
        cheap = task_type in CHEAP_TASK_TYPES
        # 低价值任务（如 summary）成本感知路由：显式覆盖优先，否则按 provider 选便宜/快档。
        # 非低价值任务的选型与改造前逐字节一致（零回归）。
        if cheap and s.summary_model:
            return s.summary_model
        if self._has_openai_compat():
            return openai_compat.routed_model(s)
        if s.deepseek_api_key:
            return "deepseek/deepseek-chat"  # deepseek-chat 已是便宜档，无更低档
        if s.qwen_api_key:
            return "openai/qwen-turbo" if cheap else "openai/qwen-plus"
        if s.anthropic_api_key:
            return "anthropic/claude-haiku-4-5" if cheap else "anthropic/claude-sonnet-4-6"
        return "deepseek/deepseek-chat"

    def _get_api_key(self, model: str) -> str:
        s = self._settings
        if self._is_openai_compat_model(model):
            return s.openai_compat_api_key
        if "deepseek" in model:
            return s.deepseek_api_key
        if "qwen" in model:
            return s.qwen_api_key
        if "anthropic" in model or "claude" in model:
            return s.anthropic_api_key
        return ""

    def _api_base_for_model(self, model: str) -> str:
        if self._is_openai_compat_model(model):
            return self._settings.openai_compat_base_url
        return ""

    def _is_openai_compat_model(self, model: str) -> bool:
        return self._has_openai_compat() and model == openai_compat.routed_model(self._settings)

    def _has_openai_compat(self) -> bool:
        return openai_compat.has_openai_compat(self._settings)
