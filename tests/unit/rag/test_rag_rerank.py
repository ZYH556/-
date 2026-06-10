from __future__ import annotations

import reflexlearn.rag.ranking.rerank as rr
from reflexlearn.rag.schemas import ChunkMeta


class _FakeCE:
    """假 cross-encoder：按 doc 文本长度给分（越长分越高），验证排序与覆盖。"""

    def predict(self, pairs, **kwargs):
        return [float(len(p[1])) for p in pairs]


def _c(cid: str, content: str) -> ChunkMeta:
    return ChunkMeta(chunk_id=cid, content=content, source="s", relevance_score=0.0)


def test_rerank_orders_by_model_score(monkeypatch):
    """rerank 用模型分覆盖 relevance_score 并按分降序。"""
    monkeypatch.setattr(rr, "_get_reranker", lambda *a, **k: _FakeCE())
    out = rr.rerank("q", [_c("short", "短"), _c("long", "这是一段更长的内容文本用于测试")])
    assert out[0].chunk_id == "long"
    assert out[0].relevance_score == float(len("这是一段更长的内容文本用于测试"))


def test_rerank_single_chunk_skips_model(monkeypatch):
    """chunks ≤ 1 直接返回，不触发模型加载。"""
    called = {"n": 0}

    def boom(*a, **k):
        called["n"] += 1
        raise AssertionError("should not load model for single chunk")

    monkeypatch.setattr(rr, "_get_reranker", boom)
    one = [_c("a", "x")]
    assert rr.rerank("q", one) == one
    assert called["n"] == 0


def test_is_available_false_when_load_fails(monkeypatch):
    """模型加载失败 → is_available 返回 False，不抛。"""
    def boom(*a, **k):
        raise rr.RerankerUnavailable("load fail")

    monkeypatch.setattr(rr, "_get_reranker", boom)
    assert rr.is_available() is False


def test_rerank_raises_when_unavailable(monkeypatch):
    """多 chunk 但模型不可用 → 抛 RerankerUnavailable（由 service 捕获降级）。"""
    def boom(*a, **k):
        raise rr.RerankerUnavailable("load fail")

    monkeypatch.setattr(rr, "_get_reranker", boom)
    import pytest

    with pytest.raises(rr.RerankerUnavailable):
        rr.rerank("q", [_c("a", "aa"), _c("b", "bbbb")])
