"""PERF-A · skills.streaming.generate_text 流式优先生成助手单测。"""

from __future__ import annotations

import pytest

from reflexlearn.common.config import get_settings
from reflexlearn.llm_gateway.gateway import Completion, StreamChunk
from reflexlearn.skills.streaming import generate_text


class _FakeLLM:
    def __init__(self, deltas=None, *, full="", model="m1"):
        self._deltas = deltas or []
        self._full = full
        self._model = model
        self.complete_called = False
        self.stream_called = False

    async def complete(self, messages, *, task_type="generation", **kw):
        self.complete_called = True
        return Completion(text=self._full, model_used=self._model)

    async def complete_stream(self, messages, *, task_type="generation", **kw):
        self.stream_called = True
        for d in self._deltas:
            yield StreamChunk(delta=d)
        yield StreamChunk(
            done=True, completion=Completion(text="".join(self._deltas), model_used=self._model)
        )


@pytest.fixture(autouse=True)
def _streaming_on():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_generate_text_streams_to_sink_and_aggregates():
    llm = _FakeLLM(deltas=["线性", "回归", "讲解"])
    received: list[str] = []

    text, model = await generate_text(
        llm, [{"role": "user", "content": "x"}], sink=received.append
    )

    assert llm.stream_called is True
    assert llm.complete_called is False
    assert received == ["线性", "回归", "讲解"]
    assert text == "线性回归讲解"
    assert model == "m1"


@pytest.mark.asyncio
async def test_generate_text_without_sink_uses_complete():
    llm = _FakeLLM(full="一次性全文")

    text, model = await generate_text(llm, [{"role": "user", "content": "x"}], sink=None)

    assert llm.complete_called is True
    assert llm.stream_called is False
    assert text == "一次性全文"


@pytest.mark.asyncio
async def test_generate_text_streaming_disabled_forces_complete(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_STREAMING", "false")
    get_settings.cache_clear()
    llm = _FakeLLM(deltas=["不该走"], full="一次性兜底")

    text, _ = await generate_text(
        llm, [{"role": "user", "content": "x"}], sink=lambda d: None
    )

    assert llm.complete_called is True
    assert llm.stream_called is False
    assert text == "一次性兜底"


@pytest.mark.asyncio
async def test_generate_text_sink_error_does_not_break_generation():
    llm = _FakeLLM(deltas=["a", "b"])

    def boom(_delta):
        raise RuntimeError("sink 炸了")

    text, _ = await generate_text(llm, [{"role": "user", "content": "x"}], sink=boom)

    assert text == "ab"  # sink 抛错被吞，生成照常聚合
