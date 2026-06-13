"""资源详情与学习状态回写。

学习状态是行为回流的第一块拼图（docs/23 §3.1）：unread → in_progress →
done → reviewed。状态写在 resources.study_status 列（可统计、可进画像），
PG 不可用降级进程内存——绝不让详情页 500。
"""

from __future__ import annotations

import logging
import time
from typing import Literal

from pydantic import BaseModel, Field

from reflexlearn.learning.assets import LearningResource

logger = logging.getLogger(__name__)

StudyStatus = Literal["unread", "in_progress", "done", "reviewed"]
STUDY_STATUSES: tuple[str, ...] = ("unread", "in_progress", "done", "reviewed")


class ResourceDetail(BaseModel):
    resource: LearningResource
    content: str = ""
    study_status: str = "unread"
    status_updated_at: float | None = None
    goal_id: str = ""
    goal_title: str = ""
    related_open_mistakes: int = 0
    degraded: list[str] = Field(default_factory=list)


class StudyStatusResult(BaseModel):
    resource_id: str
    study_status: str
    status_updated_at: float
    degraded: list[str] = Field(default_factory=list)


class ResourceStudyStore:
    """学习状态内存兜底：key=(user_id, resource_id)。PG 写失败/无 PG 时使用。"""

    def __init__(self) -> None:
        self._memory: dict[tuple[str, str], tuple[str, float]] = {}

    def get(self, user_id: str, resource_id: str) -> tuple[str, float | None]:
        status, ts = self._memory.get((user_id, resource_id), ("unread", 0.0))
        return status, (ts or None)

    def set(self, user_id: str, resource_id: str, status: str) -> float:
        ts = time.time()
        self._memory[(user_id, resource_id)] = (status, ts)
        return ts


async def load_resource_detail(
    resource: LearningResource,
    *,
    user_id: str,
    tenant_id: str,
    pg_pool,
    study_store: ResourceStudyStore,
) -> ResourceDetail:
    """聚合详情：全文内容、学习状态、所属目标、同概念待复盘错题数。

    调用方已完成 ACL（get_resource + assert_object_access），这里只做聚合。
    """
    detail = ResourceDetail(resource=resource, content=resource.content_preview)
    if pg_pool is None:
        status, ts = study_store.get(user_id, resource.resource_id)
        detail.study_status = status
        detail.status_updated_at = ts
        detail.degraded.append("pg:unavailable")
        return detail
    try:
        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(r.content, '') AS content,
                       COALESCE(r.study_status, 'unread') AS study_status,
                       EXTRACT(EPOCH FROM r.status_updated_at)::float AS status_updated_at,
                       COALESCE(r.goal_id::text, '') AS goal_id,
                       COALESCE(g.goal_text, '') AS goal_title,
                       COALESCE(r.concept, '') AS concept
                FROM resources r
                LEFT JOIN learning_goals g ON g.id = r.goal_id
                WHERE r.id::text = $1
                """,
                resource.resource_id,
            )
            if row is None:
                # 内存态资源（保存闭环降级路径产生）：状态走内存兜底
                status, ts = study_store.get(user_id, resource.resource_id)
                detail.study_status = status
                detail.status_updated_at = ts
                detail.degraded.append("pg:row_missing")
                return detail
            detail.content = row["content"] or resource.content_preview
            detail.study_status = row["study_status"]
            detail.status_updated_at = row["status_updated_at"]
            detail.goal_id = row["goal_id"]
            detail.goal_title = row["goal_title"]
            concept = row["concept"]
            if concept:
                count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM mistakes
                    WHERE tenant_id=$1 AND user_id=$2 AND concept=$3 AND status='open'
                    """,
                    tenant_id,
                    user_id,
                    concept,
                )
                detail.related_open_mistakes = int(count or 0)
    except Exception as exc:
        logger.info("resource detail degraded: %s", exc)
        status, ts = study_store.get(user_id, resource.resource_id)
        detail.study_status = status
        detail.status_updated_at = ts
        detail.degraded.append("pg:detail_unavailable")
    return detail


async def update_study_status(
    resource_id: str,
    status: str,
    *,
    user_id: str,
    pg_pool,
    study_store: ResourceStudyStore,
) -> StudyStatusResult:
    """状态回写：PG UPDATE 优先；行不存在或 PG 不可用落内存（同键覆盖）。"""
    result = StudyStatusResult(
        resource_id=resource_id, study_status=status, status_updated_at=time.time()
    )
    if pg_pool is not None:
        try:
            async with pg_pool.acquire() as conn:
                tag = await conn.execute(
                    """
                    UPDATE resources SET study_status=$2, status_updated_at=NOW()
                    WHERE id::text=$1
                    """,
                    resource_id,
                    status,
                )
            if tag and tag.endswith("1"):
                return result
            result.degraded.append("pg:row_missing")
        except Exception as exc:
            logger.info("study status pg write degraded: %s", exc)
            result.degraded.append("pg:write_failed")
    else:
        result.degraded.append("pg:unavailable")
    result.status_updated_at = study_store.set(user_id, resource_id, status)
    return result
