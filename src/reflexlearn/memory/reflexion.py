"""Reflexion 经验记忆：失败反思的语义写入与召回（真实向量 + 语义检索 + 降级）。

写入：critic 归因失败 → reflection。PG 持久化（durable record）+ Qdrant 语义索引。
召回：planner 执行前按「当前学习目标」语义召回最相关的历史失败经验，规避重蹈覆辙。

降级原则（纯增强、零破坏）：
- 写入：embedding 不可用 → 跳过 Qdrant 向量写入（绝不写零向量污染语义空间），PG 仍持久化。
- 召回：embedding 不可用 / 语义查询异常 → 降级 scroll（保留原「近 N 条」行为）；qdrant 不可用 → 空。
"""
from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from reflexlearn.common.config import get_settings
from reflexlearn.observability.metrics import observe_memory_recall
from reflexlearn.orchestration.schemas import Reflection

logger = logging.getLogger(__name__)

EXPERIENCE_COLLECTION = "experience_memory"


async def write_reflection(
    *,
    pg_pool,
    qdrant,
    reflection: Reflection,
    user_id: str,
    created_at: str = "",
) -> bool:
    wrote_any = False

    if pg_pool is not None:
        wrote_any = await _write_pg(pg_pool, reflection) or wrote_any

    if qdrant is not None:
        wrote_any = await _write_qdrant(qdrant, reflection, user_id, created_at) or wrote_any

    return wrote_any


async def recall_reflections(
    *,
    qdrant,
    task_type: str,
    query: str,
    acl: dict,
    limit: int = 3,
) -> list[dict]:
    if qdrant is None:
        observe_memory_recall(mode="none", status="unavailable", result_count=0)
        return []

    user_id = (acl or {}).get("user_id")

    # 优先语义召回：embed 当前学习目标 → 按相似度取最相关的历史失败经验
    mode = "semantic"
    points = await _semantic_recall(qdrant, query, acl, task_type, limit)
    if points is None:
        # embedding 不可用 / 语义查询失败 → 降级 scroll（保留原「近 N 条」行为）
        mode = "scroll"
        points = await _scroll_recall(qdrant, limit)
    if points is None:
        observe_memory_recall(mode=mode, status="unavailable", result_count=0)
        return []

    recalled: list[dict] = []
    for point in points:
        payload = getattr(point, "payload", None) or {}
        if not _passes_acl(payload, user_id, task_type):  # 防御性 ACL 兜底
            continue
        if _memory_consolidation_enabled():
            await _bump_hit_count(qdrant, getattr(point, "id", None), payload)
        recalled.append(
            {
                "task_type": payload.get("task_type", task_type),
                "failure_type": payload.get("failure_type", ""),
                "cause": payload.get("cause", ""),
                "fix_strategy": payload.get("fix_strategy", ""),
                "success": payload.get("success", False),
                "query": query,
            }
        )
    status = "ok" if recalled else "empty"
    observe_memory_recall(mode=mode, status=status, result_count=len(recalled))
    return recalled


async def _semantic_recall(qdrant, query: str, acl: dict, task_type: str, limit: int):
    """语义召回，返回 points 列表；embedding 不可用或查询异常返回 None（触发降级）。"""
    if not (query or "").strip():
        return None

    timeout_s = _rag_timeout_s()
    try:  # RAG 关闭即跳过 embedding，降级 scroll（与 RetrieveSkill 门控一致，亦免无谓加载模型）
        settings = get_settings()
        if not settings.enable_rag:
            return None
    except Exception:
        pass
    if not await _collection_ready(qdrant, EXPERIENCE_COLLECTION, timeout_s):
        return []

    try:
        from reflexlearn.common.embedding import embed_query

        vector = embed_query(query)
    except Exception as e:  # EmbeddingUnavailable / 依赖缺失
        logger.info("reflexion recall degraded (embedding unavailable): %s", e)
        return None

    try:
        response = await asyncio.wait_for(
            qdrant.query_points(
                collection_name=EXPERIENCE_COLLECTION,
                query=vector,
                limit=limit,
                query_filter=_build_acl_filter(acl, task_type),
                with_payload=True,
            ),
            timeout=timeout_s,
        )
        return response.points
    except Exception as e:
        logger.info("reflexion recall semantic query failed, fallback to scroll: %s", e)
        return None


async def _scroll_recall(qdrant, limit: int):
    """降级召回：scroll 取近 N 条（embedding 不可用时的兜底，保留历史行为）。"""
    try:
        points, _ = await asyncio.wait_for(
            qdrant.scroll(
                collection_name=EXPERIENCE_COLLECTION,
                limit=limit,
                with_payload=True,
            ),
            timeout=_rag_timeout_s(),
        )
        return points
    except Exception:
        return None


async def _bump_hit_count(qdrant, point_id, payload: dict) -> None:
    """召回即巩固：best-effort 增加 hit_count，任何异常都不影响主召回。"""
    if point_id is None or not hasattr(qdrant, "set_payload"):
        return
    try:
        next_count = int(payload.get("hit_count", 0)) + 1
        await qdrant.set_payload(
            collection_name=EXPERIENCE_COLLECTION,
            payload={"hit_count": next_count},
            points=[point_id],
        )
    except Exception:
        return


def _memory_consolidation_enabled() -> bool:
    try:
        return bool(getattr(get_settings(), "enable_memory_consolidation", True))
    except Exception:
        return True


def _passes_acl(payload: dict, user_id: str | None, task_type: str) -> bool:
    """内存侧 ACL 兜底（None 视为通配，与历史行为一致）：qdrant 侧过滤构建失败时仍能挡跨用户。"""
    if user_id and payload.get("user_id") not in {None, user_id}:
        return False
    if task_type and payload.get("task_type") not in {None, task_type}:
        return False
    return True


def _build_acl_filter(acl: dict, task_type: str):
    """按 user_id（+ 非空 task_type）构造 qdrant 过滤：只召回本人经验。"""
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue
    except Exception:
        return None

    must = []
    user_id = (acl or {}).get("user_id")
    if user_id:
        must.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
    if task_type:
        must.append(FieldCondition(key="task_type", match=MatchValue(value=task_type)))
    return Filter(must=must) if must else None


def _reflection_text(reflection: Reflection) -> str:
    """组合反思的语义要素，使失败经验可按当前学习目标语义召回。"""
    parts = [
        reflection.task_type,
        reflection.failure_type,
        reflection.cause,
        reflection.fix_strategy,
    ]
    return " ".join(p for p in parts if p).strip()


async def _write_pg(pg_pool, reflection: Reflection) -> bool:
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO reflections (
                    run_id, failure_type, cause, fix_strategy, embedded_id
                )
                VALUES (NULL, $1, $2, $3, NULL)
                """,
                reflection.failure_type,
                reflection.cause,
                reflection.fix_strategy,
            )
        return True
    except Exception:
        return False


async def _write_qdrant(qdrant, reflection: Reflection, user_id: str, created_at: str) -> bool:
    try:  # RAG 关闭即不写向量库（PG 已持久化），与 recall 门控一致、避免无谓加载模型
        if not get_settings().enable_rag:
            return False
    except Exception:
        pass
    if not await _collection_ready(qdrant, EXPERIENCE_COLLECTION, _rag_timeout_s()):
        return False

    # 1) 真实向量化（embedding 不可用即跳过：绝不写零向量污染语义空间，PG 已持久化）
    try:
        from reflexlearn.common.embedding import embed_documents

        vectors = embed_documents([_reflection_text(reflection)])
        if not vectors:
            return False
        vector = vectors[0]
    except Exception as e:  # EmbeddingUnavailable / 依赖缺失
        logger.info("reflexion qdrant write skipped (embedding unavailable): %s", e)
        return False

    # 2) upsert（任何异常即视为未写入，由 PG 兜底持久化）
    try:
        from qdrant_client.models import PointStruct

        await qdrant.upsert(
            collection_name=EXPERIENCE_COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "user_id": user_id,
                        "task_type": reflection.task_type,
                        "failure_type": reflection.failure_type,
                        "cause": reflection.cause,
                        "fix_strategy": reflection.fix_strategy,
                        "success": reflection.success,
                        "created_at": created_at,
                        "hit_count": 0,
                    },
                )
            ],
        )
        return True
    except Exception as e:
        logger.warning("reflexion qdrant write failed: %s", e)
        return False


def _rag_timeout_s() -> float:
    try:
        return float(getattr(get_settings(), "rag_route_timeout_s", 3.0))
    except Exception:
        return 3.0


async def _collection_ready(qdrant, collection: str, timeout_s: float) -> bool:
    checker = getattr(qdrant, "collection_exists", None)
    if checker is None:
        return True
    try:
        exists = await asyncio.wait_for(checker(collection), timeout=timeout_s)
    except TypeError:
        exists = await asyncio.wait_for(checker(collection_name=collection), timeout=timeout_s)
    except Exception as e:
        logger.info("reflexion qdrant collection check failed: %s", e)
        return False
    return bool(exists)
