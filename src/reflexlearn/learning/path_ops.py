"""学习路径节点操作：读真实 path_items、标完成、插入补救节点。

/plan 此前展示画像合成的三段示意；本模块让它吃到 PG 真实路径
（learning_goals → learning_paths → path_items），节点操作回写
mastery_status 并重算目标 progress——「标完成」是路径侧的行为回流。
路径数据只存 PG：不可用时读返回空（上层回落合成示意）、写返回
degraded 不假装成功。
"""

from __future__ import annotations

import logging

from reflexlearn.learning.path_models import (
    PathItemView,
    PathOpResult,
    PathOwnershipError,
)
from reflexlearn.learning.path_resources import merge_resources, resources_by_concept, resources_by_id

logger = logging.getLogger(__name__)

ALLOWED_ITEM_STATUSES = ("not_started", "in_progress", "done")


async def load_active_path_items(*, user_id: str, tenant_id: str, pg_pool) -> list[PathItemView]:
    """当前活跃目标的最新路径节点（sequence 升序）；无 PG/无路径返回空。"""
    if pg_pool is None:
        return []
    try:
        async with pg_pool.acquire() as conn:
            path_id = await conn.fetchval(
                """
                SELECT lp.id FROM learning_paths lp
                JOIN learning_goals lg ON lg.id = lp.goal_id
                WHERE lg.user_id=$1 AND lg.tenant_id=$2 AND COALESCE(lg.status,'active')='active'
                ORDER BY lg.created_at DESC, lp.id DESC
                LIMIT 1
                """,
                user_id,
                tenant_id,
            )
            if path_id is None:
                return []
            rows = await conn.fetch(
                """
                SELECT id, sequence, concept, objective, rationale,
                       COALESCE(mastery_status, 'not_started') AS mastery_status,
                       COALESCE(resource_id::text, '') AS pinned_resource_id
                FROM path_items WHERE path_id=$1
                ORDER BY sequence, id
                """,
                path_id,
            )
            # 节点按 concept 自动关联资源（批量查一次，内存分组）：让路径每一步
            # 有具体资源支撑，无需手动绑定。匹配不上的泛节点（如「建立直觉」）资源为空。
            concepts = [str(row["concept"]) for row in rows if row["concept"]]
            by_concept = await resources_by_concept(
                conn, concepts, user_id=user_id, tenant_id=tenant_id
            )
            # 用户显式绑定的资源（path_items.resource_id）：置顶 + 标 pinned
            pinned_ids = [str(row["pinned_resource_id"]) for row in rows if row["pinned_resource_id"]]
            pinned_map = await resources_by_id(conn, pinned_ids)
        return [
            PathItemView(
                item_id=int(row["id"]),
                sequence=int(row["sequence"] or 0),
                concept=str(row["concept"] or ""),
                objective=str(row["objective"] or ""),
                rationale=str(row["rationale"] or ""),
                mastery_status=str(row["mastery_status"]),
                resources=merge_resources(
                    pinned_map.get(str(row["pinned_resource_id"])),
                    by_concept.get(str(row["concept"] or ""), []),
                ),
            )
            for row in rows
        ]
    except Exception as exc:
        logger.info("active path items degraded: %s", exc)
        return []


async def _owned_path_id(conn, item_id: int, *, user_id: str, tenant_id: str) -> int:
    row = await conn.fetchrow(
        """
        SELECT pi.path_id, lg.user_id, lg.tenant_id
        FROM path_items pi
        JOIN learning_paths lp ON lp.id = pi.path_id
        JOIN learning_goals lg ON lg.id = lp.goal_id
        WHERE pi.id=$1
        """,
        item_id,
    )
    if row is None:
        raise LookupError("path_item_not_found")
    if row["user_id"] != user_id or row["tenant_id"] != tenant_id:
        raise PathOwnershipError("path_item_forbidden")
    return int(row["path_id"])


async def _recalc_goal_progress(conn, path_id: int) -> tuple[float, int, int]:
    stats = await conn.fetchrow(
        """
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE mastery_status='done') AS done
        FROM path_items WHERE path_id=$1
        """,
        path_id,
    )
    total = int(stats["total"] or 0)
    done = int(stats["done"] or 0)
    progress = round(done / total, 4) if total else 0.0
    await conn.execute(
        """
        UPDATE learning_goals SET progress=$2
        WHERE id = (SELECT goal_id FROM learning_paths WHERE id=$1)
        """,
        path_id,
        progress,
    )
    return progress, done, total


async def update_item_status(
    item_id: int,
    status: str,
    *,
    user_id: str,
    tenant_id: str,
    pg_pool,
) -> PathOpResult:
    """更新节点掌握状态并重算目标 progress。403/404 由调用方按异常转码。"""
    if pg_pool is None:
        return PathOpResult(ok=False, item_id=item_id, degraded=["pg:unavailable"])
    try:
        async with pg_pool.acquire() as conn:
            path_id = await _owned_path_id(conn, item_id, user_id=user_id, tenant_id=tenant_id)
            await conn.execute(
                "UPDATE path_items SET mastery_status=$2 WHERE id=$1",
                item_id,
                status,
            )
            progress, done, total = await _recalc_goal_progress(conn, path_id)
        return PathOpResult(
            ok=True,
            item_id=item_id,
            mastery_status=status,
            goal_progress=progress,
            done_items=done,
            total_items=total,
        )
    except (LookupError, PathOwnershipError):
        raise
    except Exception as exc:
        logger.info("path item status degraded: %s", exc)
        return PathOpResult(ok=False, item_id=item_id, degraded=["pg:write_failed"])


async def insert_remedial_item(
    after_item_id: int,
    *,
    concept: str,
    objective: str,
    rationale: str,
    user_id: str,
    tenant_id: str,
    pg_pool,
) -> PathOpResult:
    """在指定节点后插入补救节点（sequence 后移重排），错题飞轮的路径入口。"""
    if pg_pool is None:
        return PathOpResult(ok=False, degraded=["pg:unavailable"])
    try:
        async with pg_pool.acquire() as conn:
            path_id = await _owned_path_id(
                conn, after_item_id, user_id=user_id, tenant_id=tenant_id
            )
            after_seq = await conn.fetchval(
                "SELECT sequence FROM path_items WHERE id=$1", after_item_id
            )
            base_seq = int(after_seq or 0)
            await conn.execute(
                "UPDATE path_items SET sequence=sequence+1 WHERE path_id=$1 AND sequence>$2",
                path_id,
                base_seq,
            )
            new_id = await conn.fetchval(
                """
                INSERT INTO path_items (
                    path_id, sequence, task_ref, resource_type, concept,
                    objective, rationale, difficulty, mastery_status
                )
                VALUES ($1, $2, $3, 'ai_document', $4, $5, $6, 0.5, 'not_started')
                RETURNING id
                """,
                path_id,
                base_seq + 1,
                f"remedial-{concept or 'mistake'}",
                concept,
                objective,
                rationale,
            )
            progress, done, total = await _recalc_goal_progress(conn, path_id)
        return PathOpResult(
            ok=True,
            item_id=int(new_id),
            mastery_status="not_started",
            goal_progress=progress,
            done_items=done,
            total_items=total,
        )
    except (LookupError, PathOwnershipError):
        raise
    except Exception as exc:
        logger.info("path remedial insert degraded: %s", exc)
        return PathOpResult(ok=False, degraded=["pg:write_failed"])


async def pin_resource_to_item(
    item_id: int,
    resource_id: str,
    *,
    user_id: str,
    tenant_id: str,
    pg_pool,
) -> PathOpResult:
    """把资源显式绑定到路径节点（path_items.resource_id）。节点与资源都须属本
    用户/租户——任一不属拒绝（ACL 命门：绑别人的资源 = 越权读）。资源可置空解绑。"""
    if pg_pool is None:
        return PathOpResult(ok=False, item_id=item_id, degraded=["pg:unavailable"])
    try:
        async with pg_pool.acquire() as conn:
            path_id = await _owned_path_id(conn, item_id, user_id=user_id, tenant_id=tenant_id)
            if resource_id:
                owned = await conn.fetchval(
                    """
                    SELECT 1 FROM resources
                    WHERE id::text=$1 AND user_id=$2 AND tenant_id=$3
                    """,
                    resource_id,
                    user_id,
                    tenant_id,
                )
                if not owned:
                    raise PathOwnershipError("resource_forbidden")
            await conn.execute(
                "UPDATE path_items SET resource_id=$2 WHERE id=$1",
                item_id,
                resource_id or None,
            )
            progress, done, total = await _recalc_goal_progress(conn, path_id)
        return PathOpResult(
            ok=True,
            item_id=item_id,
            goal_progress=progress,
            done_items=done,
            total_items=total,
        )
    except (LookupError, PathOwnershipError):
        raise
    except Exception as exc:
        logger.info("path pin resource degraded: %s", exc)
        return PathOpResult(ok=False, item_id=item_id, degraded=["pg:write_failed"])
