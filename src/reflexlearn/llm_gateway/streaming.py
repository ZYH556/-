"""PERF-A · LLMGateway 的流式生成实现（从 gateway.py 拆出以守 300 行预算）。

对外只经 `LLMGateway.complete_stream()` 调用；这里的函数都接受 gateway 实例 `gw`，
复用其 `_select_model/_get_api_key/_is_openai_compat_model/_api_base_for_model/complete`。
降级铁律见 `complete_stream` docstring。
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Optional

from reflexlearn.llm_gateway import openai_compat
from reflexlearn.llm_gateway.models import Completion, StreamChunk
from reflexlearn.observability.metrics import observe_degradation, observe_llm


async def complete_stream(
    gw,
    messages: list[dict],
    *,
    task_type: str = "generation",
    temperature: float = 0.7,
) -> AsyncIterator[StreamChunk]:
    """逐 chunk yield 文本增量；末帧 done=True 带聚合 Completion。

    降级铁律：流式失败且**尚未产出任何增量** → 回退一次性 complete()，整段作为单帧
    yield（degraded=True）；已产出部分后失败 → 以已收内容收尾、记降级、不重复回退
    （避免文本重复）。无凭证 / generation 关闭仍按 complete() 抛错，交上层走本地兜底。
    schema 类任务不走流式（JSON 需整体解析），调用方用 complete()。
    """
    if task_type == "generation" and not gw._settings.enable_llm_generation:
        observe_degradation("llm", "generation_disabled")
        raise RuntimeError("generation_disabled_no_api_key")
    model = gw._select_model(task_type)
    api_key = gw._get_api_key(model)
    if not api_key:
        observe_llm(task_type=task_type, model=model, status="no_key", latency_ms=0)
        observe_degradation("llm", "no_api_key")
        raise RuntimeError("llm_no_api_key")

    if gw._is_openai_compat_model(model):
        stream = _stream_openai_compat(
            gw, model=model, messages=messages, task_type=task_type, temperature=temperature
        )
    else:
        stream = _stream_litellm(
            gw,
            model=model,
            api_key=api_key,
            messages=messages,
            task_type=task_type,
            temperature=temperature,
        )
    async for chunk in stream:
        yield chunk


async def _stream_litellm(
    gw,
    *,
    model: str,
    api_key: str,
    messages: list[dict],
    task_type: str,
    temperature: float,
) -> AsyncIterator[StreamChunk]:
    import litellm

    start = time.time()
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "timeout": gw._settings.llm_request_timeout_s,
        "stream": True,
    }
    if api_key:
        kwargs["api_key"] = api_key
    api_base = gw._api_base_for_model(model)
    if api_base:
        kwargs["api_base"] = api_base

    parts: list[str] = []
    try:
        resp = await litellm.acompletion(**kwargs)
        async for chunk in resp:
            delta = _litellm_chunk_delta(chunk)
            if delta:
                parts.append(delta)
                yield StreamChunk(delta=delta)
    except Exception as e:
        async for chunk in _stream_recover(
            gw, parts, e, model=model, task_type=task_type, start=start,
            messages=messages, temperature=temperature,
        ):
            yield chunk
        return
    yield _stream_finalize(parts, model=model, task_type=task_type, start=start)


async def _stream_openai_compat(
    gw,
    *,
    model: str,
    messages: list[dict],
    task_type: str,
    temperature: float,
) -> AsyncIterator[StreamChunk]:
    from reflexlearn.llm_gateway import http_client

    start = time.time()
    wire_api = openai_compat.wire_api(gw._settings)
    payload = openai_compat.stream_payload(
        gw._settings, messages=messages, temperature=temperature, api=wire_api, model=model
    )
    headers = {
        "Authorization": f"Bearer {gw._settings.openai_compat_api_key}",
        "Content-Type": "application/json",
    }
    url = openai_compat.request_url(gw._settings, wire_api)
    client = http_client.get_async_client(gw._settings)  # 复用连接池（PERF-C）

    parts: list[str] = []
    try:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                event = _sse_json(line)
                if event is None:
                    continue
                delta = openai_compat.stream_delta(event, wire_api)
                if delta:
                    parts.append(delta)
                    yield StreamChunk(delta=delta)
    except Exception as e:
        async for chunk in _stream_recover(
            gw, parts, e, model=model, task_type=task_type, start=start,
            messages=messages, temperature=temperature,
        ):
            yield chunk
        return
    yield _stream_finalize(parts, model=model, task_type=task_type, start=start)


def _stream_finalize(parts: list[str], *, model: str, task_type: str, start: float) -> StreamChunk:
    text = "".join(parts)
    latency = int((time.time() - start) * 1000)
    observe_llm(task_type=task_type, model=model, status="ok", latency_ms=latency)
    return StreamChunk(
        done=True,
        completion=Completion(text=text, model_used=model, latency_ms=latency),
    )


async def _stream_recover(
    gw,
    parts: list[str],
    exc: Exception,
    *,
    model: str,
    task_type: str,
    start: float,
    messages: list[dict],
    temperature: float,
) -> AsyncIterator[StreamChunk]:
    """流式失败的收尾：未产出增量 → 一次性回退；已产出 → 用已收内容收尾不重复回退。"""
    latency = int((time.time() - start) * 1000)
    observe_llm(task_type=task_type, model=model, status="error", latency_ms=latency)
    observe_degradation("llm", type(exc).__name__)
    if parts:
        text = "".join(parts)
        yield StreamChunk(
            done=True,
            degraded=True,
            completion=Completion(text=text, model_used=model, latency_ms=latency),
        )
        return
    # 尚无增量：退回一次性 complete()（失败则继续抛，交上层走本地兜底）
    observe_degradation("llm", "stream_fallback")
    completion = await gw.complete(messages, task_type=task_type, temperature=temperature)
    yield StreamChunk(delta=completion.text, done=True, degraded=True, completion=completion)


def _litellm_chunk_delta(chunk: object) -> str:
    """从 litellm 流式 chunk 取增量文本；结构异常一律返回空串（不让解析错误中断流）。"""
    try:
        choices = chunk.choices  # type: ignore[attr-defined]
        if not choices:
            return ""
        delta = choices[0].delta
        content = getattr(delta, "content", None)
        return content if isinstance(content, str) else ""
    except Exception:
        return ""


def _sse_json(line: str) -> Optional[dict]:
    """解析单行 SSE：`data: {...}` → dict；空行 / 注释 / `[DONE]` / 非 JSON → None。"""
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    data = line[len("data:"):].strip()
    if not data or data == "[DONE]":
        return None
    try:
        obj = json.loads(data)
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None
