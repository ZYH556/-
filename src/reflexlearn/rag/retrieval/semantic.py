"""语义检索（Qdrant 向量召回 + bge embedding）。提取自 skills/retrieve.py 的 query_points 逻辑。

embedding 不可用 / qdrant 异常时返回 []（不抛），由 RAGService 视为该路无结果（绝不假装成功）。
ACL 经 build_qdrant_filter 下推到查询层做物理隔离。
"""
from __future__ import annotations

import asyncio
import logging

from reflexlearn.rag.access.acl import build_qdrant_filter
from reflexlearn.rag.schemas import ChunkMeta

logger = logging.getLogger(__name__)


async def semantic_search(
    query: str,
    acl: dict,
    top_k: int,
    collection: str,
    *,
    route_timeout_s: float = 3.0,
) -> list[ChunkMeta]:
    # 1) 先轻量确认 Qdrant collection 可用；不可用时避免加载 2GB embedding 模型。
    try:
        from reflexlearn.common.db import get_qdrant

        qdrant = get_qdrant()
        if not await _collection_ready(qdrant, collection, route_timeout_s):
            return []
    except Exception as e:
        logger.warning("semantic degraded (qdrant precheck failed): %s", e)
        return []

    # 2) 查询向量化（embedding 不可用即降级该路）
    try:
        from reflexlearn.common.embedding import embed_query

        vector = embed_query(query)
    except Exception as e:
        logger.info("semantic degraded (embedding unavailable): %s", e)
        return []

    # 3) 向量检索 + ACL 下推
    try:
        response = await asyncio.wait_for(
            qdrant.query_points(
                collection_name=collection,
                query=vector,
                limit=top_k,
                query_filter=build_qdrant_filter(acl),
                with_payload=True,
            ),
            timeout=route_timeout_s,
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


async def _collection_ready(qdrant, collection: str, timeout_s: float) -> bool:
    checker = getattr(qdrant, "collection_exists", None)
    if checker is None:
        return True
    try:
        exists = await asyncio.wait_for(checker(collection), timeout=timeout_s)
    except TypeError:
        exists = await asyncio.wait_for(checker(collection_name=collection), timeout=timeout_s)
    except Exception as e:
        logger.warning("semantic degraded (collection check failed): %s", e)
        return False
    if not exists:
        logger.info("semantic degraded (collection missing): %s", collection)
    return bool(exists)
