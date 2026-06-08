"""语义检索（Qdrant 向量召回 + bge embedding）。提取自 skills/retrieve.py 的 query_points 逻辑。

embedding 不可用 / qdrant 异常时返回 []（不抛），由 RAGService 视为该路无结果（绝不假装成功）。
ACL 经 build_qdrant_filter 下推到查询层做物理隔离。
"""
from __future__ import annotations

import logging

from reflexlearn.rag.acl import build_qdrant_filter
from reflexlearn.rag.schemas import ChunkMeta

logger = logging.getLogger(__name__)


async def semantic_search(query: str, acl: dict, top_k: int, collection: str) -> list[ChunkMeta]:
    # 1) 查询向量化（embedding 不可用即降级该路）
    try:
        from reflexlearn.common.embedding import embed_query

        vector = embed_query(query)
    except Exception as e:
        logger.info("semantic degraded (embedding unavailable): %s", e)
        return []

    # 2) 向量检索 + ACL 下推
    try:
        from reflexlearn.common.db import get_qdrant

        qdrant = get_qdrant()
        response = await qdrant.query_points(
            collection_name=collection,
            query=vector,
            limit=top_k,
            query_filter=build_qdrant_filter(acl),
            with_payload=True,
        )
        hits = response.points
    except Exception as e:
        logger.warning("semantic degraded (qdrant failed): %s", e)
        return []

    out: list[ChunkMeta] = []
    for h in hits:
        payload = getattr(h, "payload", None) or {}
        content = payload.get("content", "")
        if not content:
            continue
        out.append(
            ChunkMeta(
                chunk_id=str(getattr(h, "id", "")),
                content=content,
                source=payload.get("source") or payload.get("title") or collection,
                relevance_score=float(getattr(h, "score", 0.0) or 0.0),
                source_trust=float(payload.get("source_trust", 0.5)),
                origin="semantic",
            )
        )
    return out
