from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel

from reflexlearn.common.config import get_settings
from reflexlearn.llm_gateway import http_client, openai_compat, streaming as _streaming
from reflexlearn.llm_gateway.models import Completion, StreamChunk
from reflexlearn.observability.metrics import observe_degradation, observe_llm

__all__ = ["LLMGateway", "Completion", "StreamChunk", "CHEAP_TASK_TYPES"]


# 评判/低价值类任务走便宜档模型（docs §2 成本感知路由 + docs/19 PERF-B 砍前置时延）。
# 只含「评判/反思/摘要」——绝不含 generation/planning/profiling（它们定核心产出与个性化）。
CHEAP_TASK_TYPES = {"summary", "verification", "judgment", "reasoning"}


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

    def complete_stream(
        self,
        messages: list[dict],
        *,
        task_type: str = "generation",
        temperature: float = 0.7,
    ):
        """逐 StreamChunk yield 文本增量（PERF-A）；实现见 llm_gateway.streaming，降级铁律同。"""
        return _streaming.complete_stream(
            self, messages, task_type=task_type, temperature=temperature
        )

    async def _complete_openai_compat(
        self,
        *,
        model: str,
        messages: list[dict],
        task_type: str,
        schema: Optional[type[BaseModel]],
        temperature: float,
    ) -> Completion:
        start = time.time()
        wire_api = openai_compat.wire_api(self._settings)
        payload = openai_compat.payload(
            self._settings,
            messages=messages,
            schema=schema,
            temperature=temperature,
            api=wire_api,
            model=model,  # 便宜档选型时把实际模型名带进 wire payload
        )
        headers = {
            "Authorization": f"Bearer {self._settings.openai_compat_api_key}",
            "Content-Type": "application/json",
        }
        # 复用共享 client（keep-alive 连接池，省每调用 TCP+TLS 握手 — PERF-C）；
        # 其 timeout 已按 read/connect 分级（中转站 SYN 黑洞时 connect 5s 快速降级）。
        client = http_client.get_async_client(self._settings)
        try:
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
        # 中转站优先：评判类任务在配了便宜档时走它降时延，否则主模型（默认空=零回归）。
        if self._has_openai_compat():
            if cheap and s.openai_compat_cheap_model:
                return openai_compat.routed_model_for(s.openai_compat_cheap_model)
            return openai_compat.routed_model(s)
        # 非中转站：summary_model 显式覆盖优先，否则按 provider 选便宜/快档。
        # 非便宜任务的选型与改造前逐字节一致（零回归）。
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
        if not self._has_openai_compat():
            return False
        s = self._settings
        if model == openai_compat.routed_model(s):
            return True
        return bool(
            s.openai_compat_cheap_model
            and model == openai_compat.routed_model_for(s.openai_compat_cheap_model)
        )

    def _has_openai_compat(self) -> bool:
        return openai_compat.has_openai_compat(self._settings)
