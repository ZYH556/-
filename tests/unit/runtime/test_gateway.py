from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from reflexlearn.llm_gateway.gateway import LLMGateway


class _S:
    """最小 settings 替身，只含 _select_model / _get_api_key 关心的字段。"""

    def __init__(self, **kw):
        self.deepseek_api_key = kw.get("deepseek", "")
        self.qwen_api_key = kw.get("qwen", "")
        self.anthropic_api_key = kw.get("anthropic", "")
        self.openai_compat_api_key = kw.get("openai_compat", "")
        self.openai_compat_base_url = kw.get("openai_compat_base_url", "")
        self.openai_compat_model = kw.get("openai_compat_model", "")
        self.openai_compat_wire_api = kw.get("openai_compat_wire_api", "chat_completions")
        self.summary_model = kw.get("summary_model", "")
        self.llm_request_timeout_s = kw.get("llm_request_timeout_s", 30.0)
        self.llm_connect_timeout_s = kw.get("llm_connect_timeout_s", 5.0)


def _gw(**kw) -> LLMGateway:
    gw = LLMGateway()
    gw._settings = _S(**kw)
    return gw


class _FakeTimeout:
    """httpx.Timeout 替身：记录 default(read/write/pool) 与 connect，供断言超时分级。"""

    def __init__(self, default=None, *, connect=None, **kw):
        self.default = default
        self.connect = connect


# —— summary 成本感知路由：走便宜档 ——

def test_summary_uses_cheaper_qwen():
    gw = _gw(qwen="k")
    assert gw._select_model("summary") == "openai/qwen-turbo"
    # 非便宜任务仍走 qwen-plus（改造前行为）
    assert gw._select_model("planning") == "openai/qwen-plus"


def test_summary_uses_cheaper_anthropic():
    gw = _gw(anthropic="k")
    assert gw._select_model("summary") == "anthropic/claude-haiku-4-5"
    assert gw._select_model("generation") == "anthropic/claude-sonnet-4-6"


def test_summary_model_override_takes_precedence():
    gw = _gw(qwen="k", summary_model="openai/custom-cheap")
    assert gw._select_model("summary") == "openai/custom-cheap"
    # 覆盖只作用于便宜任务，不影响其它
    assert gw._select_model("planning") == "openai/qwen-plus"


def test_deepseek_has_no_cheaper_tier():
    gw = _gw(deepseek="k")
    assert gw._select_model("summary") == "deepseek/deepseek-chat"
    assert gw._select_model("planning") == "deepseek/deepseek-chat"


# —— 零回归：非 summary 任务选型与改造前逐字节一致 ——

def test_non_summary_selection_unchanged():
    assert _gw(deepseek="k")._select_model("planning") == "deepseek/deepseek-chat"
    assert _gw(qwen="k")._select_model("profiling") == "openai/qwen-plus"
    assert _gw(anthropic="k")._select_model("generation") == "anthropic/claude-sonnet-4-6"
    assert _gw()._select_model("planning") == "deepseek/deepseek-chat"  # 全空默认


def test_provider_priority_deepseek_first():
    # deepseek 优先于 qwen 优先于 anthropic（改造前优先级不变）
    gw = _gw(deepseek="d", qwen="q", anthropic="a")
    assert gw._select_model("summary") == "deepseek/deepseek-chat"
    assert gw._select_model("planning") == "deepseek/deepseek-chat"


def test_openai_compat_takes_priority_when_fully_configured():
    gw = _gw(
        deepseek="d",
        openai_compat="relay-key",
        openai_compat_base_url="https://timicc.com",
        openai_compat_model="gpt-5.5",
    )

    assert gw._select_model("judgment") == "openai/gpt-5.5"
    assert gw._get_api_key("openai/gpt-5.5") == "relay-key"
    assert gw._api_base_for_model("openai/gpt-5.5") == "https://timicc.com"


def test_openai_compat_requires_key_base_url_and_model():
    assert _gw(openai_compat="k", openai_compat_model="gpt-5.5")._select_model("planning") == (
        "deepseek/deepseek-chat"
    )
    assert _gw(openai_compat="k", openai_compat_base_url="https://timicc.com")._select_model(
        "planning"
    ) == "deepseek/deepseek-chat"


# —— 无凭证：仍抛 llm_no_api_key（降级铁律入口） ——

@pytest.mark.asyncio
async def test_no_api_key_raises_for_summary():
    gw = _gw()  # 全空
    with pytest.raises(RuntimeError, match="llm_no_api_key"):
        await gw.complete([{"role": "user", "content": "hi"}], task_type="summary")


def test_get_api_key_matches_cheaper_models():
    # 新增便宜档模型名仍能正确映射回各自 provider 的 key
    gw = _gw(qwen="qk", anthropic="ak")
    assert gw._get_api_key("openai/qwen-turbo") == "qk"
    assert gw._get_api_key("anthropic/claude-haiku-4-5") == "ak"


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
