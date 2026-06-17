from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from reflexlearn.llm_gateway.gateway import LLMGateway


class _S:
    """最小 settings 替身，只含 HTTP 路径测试关心的字段。"""

    def __init__(self, **kw):
        self.deepseek_api_key = kw.get("deepseek", "")
        self.qwen_api_key = kw.get("qwen", "")
        self.anthropic_api_key = kw.get("anthropic", "")
        self.openai_compat_api_key = kw.get("openai_compat", "")
        self.openai_compat_base_url = kw.get("openai_compat_base_url", "")
        self.openai_compat_model = kw.get("openai_compat_model", "")
        self.openai_compat_cheap_model = kw.get("openai_compat_cheap_model", "")
        self.openai_compat_wire_api = kw.get("openai_compat_wire_api", "chat_completions")
        self.summary_model = kw.get("summary_model", "")
        self.llm_request_timeout_s = kw.get("llm_request_timeout_s", 30.0)
        self.llm_connect_timeout_s = kw.get("llm_connect_timeout_s", 5.0)
        self.enable_llm_generation = kw.get("enable_llm_generation", True)


def _gw(**kw) -> LLMGateway:
    gw = LLMGateway()
    gw._settings = _S(**kw)
    return gw


class _FakeTimeout:
    """httpx.Timeout 替身：记录 default(read/write/pool) 与 connect，供断言超时分级。"""

    def __init__(self, default=None, *, connect=None, **kw):
        self.default = default
        self.connect = connect


@pytest.mark.asyncio
async def test_openai_compat_complete_uses_direct_http(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5},
            }

    class FakeClient:
        def __init__(self, *, timeout):
            calls.append({"timeout": timeout})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, headers, json):
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=FakeClient, Timeout=_FakeTimeout))
    gw = _gw(
        openai_compat="relay-key",
        openai_compat_base_url="https://timicc.com",
        openai_compat_model="gpt-5.5",
    )

    completion = await gw.complete(
        [{"role": "user", "content": "hi"}],
        task_type="judgment",
        temperature=0.0,
    )

    assert completion.model_used == "openai/gpt-5.5"
    assert calls[0]["timeout"].default == 30.0
    assert calls[0]["timeout"].connect == 5.0
    assert calls[1]["url"] == "https://timicc.com/v1/chat/completions"
    assert calls[1]["headers"]["Authorization"] == "Bearer relay-key"
    assert calls[1]["json"]["model"] == "gpt-5.5"


@pytest.mark.asyncio
async def test_shared_client_reused_across_calls(monkeypatch):
    """PERF-C：多次 complete() 复用同一 AsyncClient（只构造一次 = 连接池保活）。"""
    inits = {"n": 0}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    class FakeClient:
        def __init__(self, *, timeout):
            inits["n"] += 1

        async def post(self, url, *, headers, json):
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=FakeClient, Timeout=_FakeTimeout))
    gw = _gw(
        openai_compat="relay-key",
        openai_compat_base_url="https://timicc.com",
        openai_compat_model="gpt-5.5",
    )

    for _ in range(3):
        await gw.complete([{"role": "user", "content": "hi"}], task_type="judgment")

    assert inits["n"] == 1


@pytest.mark.asyncio
async def test_openai_compat_responses_uses_direct_http(monkeypatch):
    calls = []

    class ProbeShape(BaseModel):
        ok: bool

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output_text": '{"ok":true}',
                "usage": {"input_tokens": 7, "output_tokens": 11},
            }

    class FakeClient:
        def __init__(self, *, timeout):
            calls.append({"timeout": timeout})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, headers, json):
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=FakeClient, Timeout=_FakeTimeout))
    gw = _gw(
        openai_compat="relay-key",
        openai_compat_base_url="https://relay.example/v1",
        openai_compat_model="gpt-5.5",
        openai_compat_wire_api="responses",
    )

    completion = await gw.complete(
        [
            {"role": "system", "content": "只输出 JSON。"},
            {"role": "user", "content": "返回 ok=true"},
        ],
        task_type="judgment",
        schema=ProbeShape,
        temperature=0.0,
    )

    assert completion.text == '{"ok":true}'
    assert completion.input_tokens == 7
    assert completion.output_tokens == 11
    assert calls[0]["timeout"].default == 30.0
    assert calls[0]["timeout"].connect == 5.0
    assert calls[1]["url"] == "https://relay.example/v1/responses"
    assert calls[1]["headers"]["Authorization"] == "Bearer relay-key"
    assert calls[1]["json"]["model"] == "gpt-5.5"
    assert calls[1]["json"]["input"][0]["role"] == "system"
    assert calls[1]["json"]["text"]["format"]["type"] == "json_object"


@pytest.mark.asyncio
async def test_openai_compat_responses_parses_nested_output(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "nested ok"},
                        ],
                    }
                ],
                "usage": {"input_tokens": 2, "output_tokens": 4},
            }

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, *, headers, json):
            return FakeResponse()

    monkeypatch.setitem(sys.modules, "httpx", SimpleNamespace(AsyncClient=FakeClient, Timeout=_FakeTimeout))
    gw = _gw(
        openai_compat="relay-key",
        openai_compat_base_url="https://relay.example",
        openai_compat_model="gpt-5.5",
        openai_compat_wire_api="responses",
    )

    completion = await gw.complete(
        [{"role": "user", "content": "hi"}],
        task_type="judgment",
    )

    assert completion.text == "nested ok"
    assert completion.input_tokens == 2
    assert completion.output_tokens == 4
