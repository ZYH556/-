"""知识检索 Skill：委托 RAGService 三路混合检索（语义 Qdrant + 关键词 BM25 + 图谱 Neo4j）
+ rerank + ACL，离线/异常降级回 mock。

改造前为 Qdrant 单路语义；现接入 rag.RAGService。契约 100% 不变：返回
{chunks:[{chunk_id,content,source,relevance_score}]}，generator._retrieve_context 无感。
任何异常 / 全路无果 → 回退 mock，保证离线、受限网络、未入库等环境下端到端仍可跑。
"""
from __future__ import annotations

import logging
import time

from reflexlearn.common.config import get_settings
from reflexlearn.skills.base import SkillContext, SkillResult

logger = logging.getLogger(__name__)


def _mock_chunks(query: str) -> list[dict]:
    return [
        {
            "chunk_id": "mock-001",
            "content": (
                f"[Mock 检索结果] 关于「{query}」的知识片段："
                "这是一段机器学习基础知识，涵盖核心概念和应用场景。"
            ),
            "source": "mock_knowledge_base",
            "relevance_score": 0.85,
        }
    ]


class RetrieveSkill:
    name = "retrieve"
    max_calls_per_task = 6
    cache_ttl = 300

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult:
        start = time.time()
        query = (inp.get("query") or "").strip()
        query_type = inp.get("query_type") or "default"
        settings = get_settings()

        chunks: list[dict] | None = None
        if settings.enable_rag and query:
            chunks = await self._hybrid_search(query, query_type, ctx, settings)

        if not chunks:
            chunks = _mock_chunks(query or "未指定查询")  # 降级兜底

        duration = int((time.time() - start) * 1000)
        return SkillResult(ok=True, data={"chunks": chunks}, duration_ms=duration)

    async def _hybrid_search(self, query: str, query_type: str, ctx: SkillContext, settings):
        """委托 RAGService 三路混合检索；映射回 dict 契约。任何异常返回 None（→ 退 mock）。"""
        try:
            from reflexlearn.rag.service import RAGService

            svc = RAGService(settings=settings)
            result = await svc.retrieve(
                query, acl=ctx.acl or {}, query_type=query_type, top_k=settings.retrieve_top_k
            )
            chunks = [
                {
                    "chunk_id": c.chunk_id,
                    "content": c.content,
                    "source": c.source,
                    "relevance_score": c.relevance_score,
                }
                for c in result.chunks
            ]
            return chunks or None
        except Exception as e:  # RAGService 内已逐路降级，此处兜底极端异常
            logger.warning("retrieve degraded (hybrid failed): %s", e)
            return None
