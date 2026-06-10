"""多路召回结果融合与排序。

三路分数量纲不可比（cosine∈[0,1]、BM25∈[0,∞)、图扩展间接命中），故融合用 RRF
（Reciprocal Rank Fusion，只看名次、鲁棒、无需调参），不做加权混分。
排序职责分离：RRF 融合 → bge-reranker 精排（service 层）→ weighted_sort 仅在 reranker
不可用时作降级兜底（不与 rerank 串联叠加）。
"""
from __future__ import annotations

from reflexlearn.rag.schemas import ChunkMeta

RRF_K = 60  # RRF 经典默认常数


def rrf_fuse(rank_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
    """对多个「按相关性降序的 chunk_id 列表」做 RRF，返回 chunk_id -> 融合分。"""
    scores: dict[str, float] = {}
    for lst in rank_lists:
        for rank, cid in enumerate(lst):  # rank 从 0 起
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return scores


def fuse_and_dedup(routes: dict[str, list[ChunkMeta]]) -> list[ChunkMeta]:
    """融合各路（{origin: [ChunkMeta 降序]}）：RRF 打分 + 按 chunk_id 去重，返回降序列表。

    三路 chunk_id 同源（均为 Qdrant point id / graph::name），去重正确。
    relevance_score 暂填 RRF 分（rerank 后会被覆盖）。
    """
    by_id: dict[str, ChunkMeta] = {}
    rank_lists: list[list[str]] = []
    for _origin, chunks in routes.items():
        rank_lists.append([c.chunk_id for c in chunks])
        for c in chunks:
            by_id.setdefault(c.chunk_id, c)  # 首次出现为准
    rrf = rrf_fuse(rank_lists)
    ordered_ids = sorted(rrf, key=lambda cid: rrf[cid], reverse=True)
    out: list[ChunkMeta] = []
    for cid in ordered_ids:
        c = by_id[cid]
        c.relevance_score = rrf[cid]
        out.append(c)
    return out


def weighted_sort(chunks: list[ChunkMeta]) -> list[ChunkMeta]:
    """降级兜底排序：归一化当前相关性分后与 source_trust 加权（语义 0.7 + 可信度 0.3）。

    归一化让 RRF 分（量级极小）与 source_trust 可比；种子数据无 published_at，时效项退化省略。
    rerank 可用时不会走到这里。
    """
    if not chunks:
        return chunks
    vals = [c.relevance_score for c in chunks]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0
    for c in chunks:
        norm = (c.relevance_score - lo) / rng
        c.relevance_score = norm * 0.7 + c.source_trust * 0.3
    return sorted(chunks, key=lambda c: c.relevance_score, reverse=True)
