from __future__ import annotations

from collections.abc import Mapping
from typing import Optional

from pydantic import BaseModel


def has_openai_compat(settings) -> bool:
    return bool(
        settings.openai_compat_api_key
        and settings.openai_compat_base_url
        and settings.openai_compat_model
    )


def model_name(settings) -> str:
    return settings.openai_compat_model.strip().removeprefix("openai/")


def routed_model(settings) -> str:
    raw = model_name(settings)
    return raw if raw.startswith("openai/") else f"openai/{raw}"


def routed_model_for(raw: str) -> str:
    """把任意中转站模型名规范化为 openai/{name}（与 routed_model 同形，供便宜档选型）。"""
    name = (raw or "").strip().removeprefix("openai/")
    return f"openai/{name}"


def bare_model(model: str) -> str:
    """去掉 openai/ 前缀，得到中转站 wire 层要的裸模型名。"""
    return (model or "").strip().removeprefix("openai/")


def wire_api(settings) -> str:
    raw = settings.openai_compat_wire_api.strip().lower().replace("-", "_")
    return "responses" if raw == "responses" else "chat_completions"


def payload(
    settings,
    *,
    messages: list[dict],
    schema: Optional[type[BaseModel]],
    temperature: float,
    api: str,
    model: Optional[str] = None,
) -> dict:
    # model 显式传入时用它（便宜档选型）；否则取配置主模型。
    name = bare_model(model) if model else model_name(settings)
    body: dict = {"model": name, "temperature": temperature}
    if api == "responses":
        body["input"] = messages
        if schema:
            body["text"] = {"format": {"type": "json_object"}}
        return body

    body["messages"] = messages
    if schema:
        body["response_format"] = {"type": "json_object"}
    return body


def request_url(settings, api: str) -> str:
    if api == "responses":
        return responses_url(settings)
    return chat_url(settings)


def chat_url(settings) -> str:
    base = settings.openai_compat_base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def responses_url(settings) -> str:
    base = settings.openai_compat_base_url.rstrip("/")
    if base.endswith("/responses"):
        return base
    return f"{base}/responses"


def stream_payload(
    settings,
    *,
    messages: list[dict],
    temperature: float,
    api: str,
    model: Optional[str] = None,
) -> dict:
    """流式请求体：普通 payload + stream=True。流式不支持 schema（JSON 需整体解析）。"""
    body = payload(
        settings, messages=messages, schema=None, temperature=temperature, api=api, model=model
    )
    body["stream"] = True
    return body


def stream_delta(event: Mapping[str, object], api: str) -> str:
    """从单个 SSE chunk(JSON) 提取增量文本；非文本/控制帧返回空串。"""
    if api == "responses":
        return _responses_stream_delta(event)
    return _chat_stream_delta(event)


def _chat_stream_delta(event: Mapping[str, object]) -> str:
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, Mapping):
        return ""
    content = delta.get("content")
    return content if isinstance(content, str) else ""


def _responses_stream_delta(event: Mapping[str, object]) -> str:
    # responses 流式：增量帧 type=response.output_text.delta，文本在 delta 字段。
    if event.get("type") == "response.output_text.delta":
        delta = event.get("delta")
        return delta if isinstance(delta, str) else ""
    return ""


def response_text(data: Mapping[str, object], api: str) -> str:
    if api == "responses":
        return _responses_text(data)
    choices = data["choices"]
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, Mapping):
        return ""
    message = first.get("message")
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def usage_tokens(data: Mapping[str, object], api: str) -> tuple[int, int]:
    usage = data.get("usage")
    if not isinstance(usage, Mapping):
        return 0, 0
    if api == "responses":
        return (
            int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0),
            int(usage.get("output_tokens") or usage.get("completion_tokens") or 0),
        )
    return (
        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


def _responses_text(data: Mapping[str, object]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str):
        return output_text

    parts: list[str] = []
    output = data.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, Mapping):
            continue
        item_text = item.get("text")
        if isinstance(item_text, str):
            parts.append(item_text)
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                parts.append(block["text"])
    return "".join(parts)
