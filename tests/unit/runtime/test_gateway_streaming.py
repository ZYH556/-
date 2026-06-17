from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from reflexlearn.llm_gateway.gateway import LLMGateway


class _S:
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
    def __init__(self, default=None, *, connect=None, **kw):
        self.default = default
        self.connect = connect

# —— PERF-A · complete_stream() 流式能力 ——


async def _collect(stream):
    return [c async for c in stream]


def _fake_stream_httpx(lines, *, raise_on_status=False, raise_mid=False):
    """构造 httpx 替身：client.stream(...) 逐行 yield SSE 文本行。"""
    calls: list = []

    class FakeStreamResp:
        def raise_for_status(self):
            if raise_on_status:
                raise RuntimeError("relay_502")

        async def aiter_lines(self):
            for ln in lines:
                yield ln
            if raise_mid:
                raise RuntimeError("stream_broke")

    class StreamCtx:
        async def __aenter__(self):
            return FakeStreamResp()

        async def __aexit__(self, *a):
            return None

    class FakeClient:
        def __init__(self, *, timeout):
            calls.append({"timeout": timeout})

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        def stream(self, method, url, *, headers, json):
            calls.append({"method": method, "url": url, "json": json})
            return StreamCtx()

    return SimpleNamespace(AsyncClient=FakeClient, Timeout=_FakeTimeout), calls


def _compat_gw(**kw):
    return _gw(
        openai_compat="relay-key",
        openai_compat_base_url=kw.pop("base_url", "https://timicc.com"),
        openai_compat_model="gpt-5.5",
        **kw,
    )


@pytest.mark.asyncio
async def test_complete_stream_compat_yields_deltas_then_done(monkeypatch):
    lines = [
        'data: {"choices":[{"delta":{"content":"线性"}}]}',
        "",
        'data: {"choices":[{"delta":{"content":"回归"}}]}',
        "data: [DONE]",
    ]
    fake_httpx, calls = _fake_stream_httpx(lines)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    gw = _compat_gw()

    chunks = await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))

    deltas = [c.delta for c in chunks if not c.done]
    assert deltas == ["线性", "回归"]
    last = chunks[-1]
    assert last.done is True
    assert last.degraded is False
    assert last.completion.text == "线性回归"
    # stream() 带 stream=True、走 chat/completions
    assert calls[1]["json"]["stream"] is True
    assert calls[1]["url"].endswith("/v1/chat/completions")


@pytest.mark.asyncio
async def test_complete_stream_responses_wire_api(monkeypatch):
    lines = [
        'data: {"type":"response.output_text.delta","delta":"ok-"}',
        'data: {"type":"response.completed"}',
        'data: {"type":"response.output_text.delta","delta":"done"}',
    ]
    fake_httpx, calls = _fake_stream_httpx(lines)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    gw = _compat_gw(base_url="https://relay.example/v1", openai_compat_wire_api="responses")

    chunks = await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))

    assert [c.delta for c in chunks if not c.done] == ["ok-", "done"]
    assert chunks[-1].completion.text == "ok-done"
    assert calls[1]["url"].endswith("/responses")


@pytest.mark.asyncio
async def test_complete_stream_falls_back_when_status_fails(monkeypatch):
    """连上但立刻 502（未产出增量）→ 回退一次性 complete()，degraded 单帧。"""
    fake_httpx, _ = _fake_stream_httpx([], raise_on_status=True)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    gw = _compat_gw()

    async def fake_complete(messages, *, task_type, temperature):
        from reflexlearn.llm_gateway.gateway import Completion

        return Completion(text="一次性兜底全文", model_used="openai/gpt-5.5")

    monkeypatch.setattr(gw, "complete", fake_complete)

    chunks = await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))

    assert len(chunks) == 1
    assert chunks[0].done is True
    assert chunks[0].degraded is True
    assert chunks[0].delta == "一次性兜底全文"
    assert chunks[0].completion.text == "一次性兜底全文"


@pytest.mark.asyncio
async def test_complete_stream_partial_then_break_no_duplicate(monkeypatch):
    """已产出部分后流断 → 用已收内容收尾、degraded，不重复回退（避免文本翻倍）。"""
    lines = ['data: {"choices":[{"delta":{"content":"半截"}}]}']
    fake_httpx, _ = _fake_stream_httpx(lines, raise_mid=True)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    gw = _compat_gw()

    called = {"complete": False}

    async def fake_complete(*a, **k):
        called["complete"] = True
        raise AssertionError("不应在已产出增量后再回退")

    monkeypatch.setattr(gw, "complete", fake_complete)

    chunks = await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))

    assert [c.delta for c in chunks if not c.done] == ["半截"]
    assert chunks[-1].done is True
    assert chunks[-1].degraded is True
    assert chunks[-1].completion.text == "半截"  # 不含回退重复
    assert called["complete"] is False


@pytest.mark.asyncio
async def test_complete_stream_no_api_key_raises():
    gw = _gw()  # 全空
    with pytest.raises(RuntimeError, match="llm_no_api_key"):
        await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))


@pytest.mark.asyncio
async def test_complete_stream_generation_disabled_raises():
    gw = _gw(deepseek="k", enable_llm_generation=False)
    with pytest.raises(RuntimeError, match="generation_disabled"):
        await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))


@pytest.mark.asyncio
async def test_complete_stream_litellm_path(monkeypatch):
    """非 compat provider（deepseek）走 litellm stream=True 分支。"""

    class FakeStream:
        def __aiter__(self):
            async def gen():
                for piece in ["a", "b", "c"]:
                    yield SimpleNamespace(
                        choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))]
                    )
            return gen()

    async def fake_acompletion(**kwargs):
        assert kwargs["stream"] is True
        return FakeStream()

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_acompletion))
    gw = _gw(deepseek="k")

    chunks = await _collect(gw.complete_stream([{"role": "user", "content": "hi"}]))

    assert [c.delta for c in chunks if not c.done] == ["a", "b", "c"]
    assert chunks[-1].completion.text == "abc"
    assert chunks[-1].done is True
