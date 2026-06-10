from __future__ import annotations

import pytest

from reflexlearn.rag.ranking.fusion import fuse_and_dedup, rrf_fuse, weighted_sort
from reflexlearn.rag.schemas import ChunkMeta


def _c(cid: str, score: float = 0.0, trust: float = 0.5, origin: str = "semantic") -> ChunkMeta:
    return ChunkMeta(
        chunk_id=cid, content=f"内容{cid}", source="s",
        relevance_score=score, source_trust=trust, origin=origin,
    )


def test_rrf_fuse_accumulates_across_lists():
    """同一 id 在多路出现 → RRF 分累加，多路命中分更高。"""
    scores = rrf_fuse([["A", "B"], ["A", "C"]], k=60)
    assert scores["A"] == pytest.approx(1 / 61 + 1 / 61)
    assert scores["B"] == pytest.approx(1 / 62)
    assert scores["A"] > scores["B"]  # 两路命中 > 单路命中


def test_fuse_and_dedup_dedups_and_orders():
    """跨路去重（按 chunk_id），按 RRF 降序，两路命中的排第一。"""
    routes = {
        "semantic": [_c("A"), _c("B")],
        "keyword": [_c("A"), _c("C")],
    }
    out = fuse_and_dedup(routes)
    ids = [c.chunk_id for c in out]
    assert ids[0] == "A"  # A 两路命中，RRF 最高
    assert sorted(ids) == ["A", "B", "C"]  # 去重后三条
    assert len(ids) == len(set(ids))


def test_weighted_sort_prefers_high_trust_when_relevance_equal():
    """RRF 分相同 → 归一化后全靠 source_trust，高可信度靠前。"""
    out = weighted_sort([_c("low", score=0.05, trust=0.5), _c("high", score=0.05, trust=0.9)])
    assert out[0].chunk_id == "high"


def test_weighted_sort_empty_ok():
    assert weighted_sort([]) == []
