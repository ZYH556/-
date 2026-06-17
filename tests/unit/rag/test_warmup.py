"""PERF-D · rag.warmup.warm_models 启动预热门控 + 串行 + 降级。"""

from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
import reflexlearn.rag.ranking.rerank as rr
from reflexlearn.rag.warmup import warm_models


class _S:
    def __init__(self, *, warmup=True, rag=True, rerank=True):
        self.enable_model_warmup = warmup
        self.enable_rag = rag
        self.enable_rerank = rerank


@pytest.mark.asyncio
async def test_warm_models_warms_embedding_and_reranker(monkeypatch):
    calls = []
    monkeypatch.setattr(emb, "is_available", lambda: calls.append("emb") or True)
    monkeypatch.setattr(rr, "is_available", lambda: calls.append("rr") or True)

    await warm_models(_S())

    assert calls == ["emb", "rr"]  # 串行：embedding 先、reranker 后


@pytest.mark.asyncio
async def test_warm_models_skips_when_rag_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(emb, "is_available", lambda: calls.append("emb") or True)
    monkeypatch.setattr(rr, "is_available", lambda: calls.append("rr") or True)

    await warm_models(_S(rag=False))

    assert calls == []


@pytest.mark.asyncio
async def test_warm_models_skips_when_warmup_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(emb, "is_available", lambda: calls.append("emb") or True)

    await warm_models(_S(warmup=False))

    assert calls == []


@pytest.mark.asyncio
async def test_warm_models_skips_reranker_when_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(emb, "is_available", lambda: calls.append("emb") or True)
    monkeypatch.setattr(rr, "is_available", lambda: calls.append("rr") or True)

    await warm_models(_S(rerank=False))

    assert calls == ["emb"]


@pytest.mark.asyncio
async def test_warm_models_degrades_on_failure(monkeypatch):
    def boom():
        raise RuntimeError("model files missing")

    monkeypatch.setattr(emb, "is_available", boom)
    monkeypatch.setattr(rr, "is_available", lambda: True)

    # 预热内部异常被吞，不外抛（启动绝不因预热失败崩）
    await warm_models(_S())
