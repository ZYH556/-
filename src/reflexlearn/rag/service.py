"""RAGService：三路混合检索编排（语义 Qdrant + 关键词 BM25 + 图谱 Neo4j）。

七步：router 选路 → 并行召回(asyncio.gather) → RRF 融合去重 → (各路源头已做 ACL，融合后不重复)
→ rerank 精排 | weighted_sort 降级 → token 预算裁剪。

铁律落地：
- 每路独立（gather return_exceptions=True），单路失败只丢该路；全路失败返回空 chunks，永不抛到 skill 外。
- 死锁规避：gather 只并行「召回」（semantic 触发 embedding），rerank 在 gather 完成后串行执行，
  绝不让 embedding 与 reranker 推理并发。
- 门控：enable_graph_retrieval 在此收口（router 想用图也要配置开）；enable_rerank 控 rerank。

注入（测试用）：neo4j / reranker / settings 可注入；qdrant 经各子模块的 get_qdrant 单例
（测试 monkeypatch get_qdrant，与 test_retrieve 范式一致）。
"""
from __future__ import annotations

import asyncio
import logging

from reflexlearn.rag.fusion import fuse_and_dedup, weighted_sort
from reflexlearn.rag.router import route_strategy
from reflexlearn.rag.schemas import ChunkMeta, RetrievalResult

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self, *, neo4j=None, reranker=None, settings=None):
        self._neo4j = neo4j
        self._reranker = reranker  # 有 .rerank()/.is_available() 的模块或对象；None 用 rag.rerank
        self._settings = settings

    def _settings_obj(self):
        if self._settings is not None:
            return self._settings
        from reflexlearn.common.config import get_settings

        return get_settings()

    async def retrieve(self, query: str, *, acl: dict | None = None,
                       query_type: str = "default", top_k: int | None = None) -> RetrievalResult:
        acl = acl or {}
        settings = self._settings_obj()
        strategy = route_strategy(
            query, query_type, default_top_k=top_k or getattr(settings, "retrieve_top_k", 5)
        )
        use_graph = strategy.use_graph and getattr(settings, "enable_graph_retrieval", False)

        # keyword 索引（关键词路与图路都复用它命中 chunk）
        kw_index = None
        if strategy.use_keyword or use_graph:
            try:
                from reflexlearn.rag.keyword import KeywordIndex

                kw_index = await KeywordIndex.get()
            except Exception as e:
                logger.warning("keyword index unavailable: %s", e)

        # 1) 并行召回（只并行召回，不含 rerank）
        tasks = []
        order: list[str] = []
        if strategy.use_semantic:
            tasks.append(self._semantic(query, acl, strategy.top_k, settings))
            order.append("semantic")
        if strategy.use_keyword and kw_index is not None:
            tasks.append(self._keyword(kw_index, query, acl, strategy.top_k))
            order.append("keyword")
        if use_graph:
            tasks.append(self._graph(query, acl, kw_index))
            order.append("graph")

        routes: dict[str, list[ChunkMeta]] = {}
        routes_used: list[str] = []
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for name, res in zip(order, results):
                if isinstance(res, Exception):
                    logger.warning("route %s failed: %s", name, res)
                    continue
                if res:
                    routes[name] = res
                    routes_used.append(name)

        # 2) RRF 融合去重
        fused = fuse_and_dedup(routes) if routes else []
        if not fused:
            return RetrievalResult(chunks=[], strategy_used=str(strategy), routes_used=routes_used)

        # 3) rerank 精排（串行，gather 之后）| weighted_sort 降级
        ranked = self._rerank_or_fallback(query, fused, settings)

        # 4) token 预算裁剪
        final = self._trim_to_budget(ranked, strategy.top_k)
        return RetrievalResult(chunks=final, strategy_used=str(strategy), routes_used=routes_used)

    async def _semantic(self, query, acl, top_k, settings) -> list[ChunkMeta]:
        from reflexlearn.rag.semantic import semantic_search

        return await semantic_search(query, acl, top_k, getattr(settings, "knowledge_collection", "knowledge_chunks"))

    async def _keyword(self, kw_index, query, acl, top_k) -> list[ChunkMeta]:
        return kw_index.search(query, top_k=top_k, acl=acl)

    async def _graph(self, query, acl, kw_index) -> list[ChunkMeta]:
        from reflexlearn.rag.graph_retrieval import graph_expand

        neo4j = self._neo4j
        if neo4j is None:
            from reflexlearn.common.db import get_neo4j

            neo4j = get_neo4j()
        return await graph_expand(neo4j, query, acl, keyword_index=kw_index)

    def _rerank_or_fallback(self, query, chunks, settings) -> list[ChunkMeta]:
        if not getattr(settings, "enable_rerank", True):
            return weighted_sort(chunks)
        reranker = self._reranker
        if reranker is None:
            from reflexlearn.rag import rerank as reranker
        try:
            return reranker.rerank(query, chunks)
        except Exception as e:  # RerankerUnavailable / 推理异常 → 降级
            logger.info("rerank degraded -> weighted_sort: %s", e)
            return weighted_sort(chunks)

    def _trim_to_budget(self, chunks: list[ChunkMeta], top_k: int, char_budget: int = 4000) -> list[ChunkMeta]:
        out: list[ChunkMeta] = []
        total = 0
        for i, c in enumerate(chunks):
            if i >= top_k:
                break
            est = len(c.content or "")
            if out and total + est > char_budget:
                break
            out.append(c)
            total += est
        return out
