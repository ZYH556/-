"""Neo4j 知识图谱扩展检索（关键：全程不触发 embedding）。

与 docs/03 §4 骨架的根本区别：骨架对每个扩展概念再 embedder.encode（二次触发 embedding，
违反双大模型死锁铁律）。本实现改为：query → 确定性命中种子概念 → Cypher 沿 PREREQUISITE_OF/
RELATED_TO 1..2 跳扩展 → 用「相关概念名」走 keyword 索引命中已入库 chunk（命不中则把概念本身
作低分 ChunkMeta）。ACL 在 Cypher WHERE 物理注入。任何异常返回 []（绝不假装成功）。
"""
from __future__ import annotations

import logging

from reflexlearn.rag.schemas import ChunkMeta

logger = logging.getLogger(__name__)


def _extract_concepts(query: str, names: list[str]) -> list[str]:
    """确定性概念抽取（不依赖 LLM）：query 与图中概念名互相包含即命中（仿 path_plan 的 is_weak）。"""
    q = (query or "").lower()
    if not q:
        return []
    hits: list[str] = []
    for n in names:
        nl = (n or "").lower()
        if nl and (nl in q or q in nl):
            hits.append(n)
    return hits


async def _all_concept_names(neo4j, tid: str) -> list[str]:
    cypher = (
        "MATCH (c:Concept) WHERE c.tenant_id=$tid OR c.visibility='public' RETURN c.name AS name"
    )
    async with neo4j.session() as s:
        rec = await s.run(cypher, tid=tid)
        return [r.data()["name"] async for r in rec]


async def graph_expand(neo4j, query: str, acl: dict, keyword_index=None) -> list[ChunkMeta]:
    """图扩展召回。keyword_index 注入时用其命中 chunk（复用 BM25，不 embed）；否则返回概念占位。"""
    tid = acl.get("tenant_id", "default")
    try:
        names = await _all_concept_names(neo4j, tid)
        seeds = _extract_concepts(query, names)
        if not seeds:
            return []
        cypher = (
            "MATCH (c:Concept)-[:PREREQUISITE_OF|RELATED_TO*1..2]-(r:Concept) "
            "WHERE c.name IN $seeds AND (c.tenant_id=$tid OR c.visibility='public') "
            "  AND (r.tenant_id=$tid OR r.visibility='public') "
            "RETURN DISTINCT r.name AS name, r.description AS desc"
        )
        async with neo4j.session() as s:
            rec = await s.run(cypher, seeds=seeds, tid=tid)
            rows = [r.data() async for r in rec]
    except Exception as e:
        logger.warning("graph expand degraded (neo4j failed): %s", e)
        return []

    out: list[ChunkMeta] = []
    seen: set[str] = set()
    for row in rows:
        name = row.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        hits = keyword_index.search(name, top_k=2, acl=acl) if keyword_index else []
        if hits:
            for h in hits:
                h.origin = "graph"
                out.append(h)
        else:
            # 命中不到 chunk：把概念本身作低分占位（仍给下游 LLM 提供概念线索）
            desc = row.get("desc") or ""
            out.append(
                ChunkMeta(
                    chunk_id=f"graph::{name}",
                    content=f"{name}：{desc}" if desc else name,
                    source="knowledge_graph",
                    relevance_score=0.0,
                    origin="graph",
                )
            )
    return out
