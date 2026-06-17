"""路径节点关联资源的读侧辅助。"""

from __future__ import annotations

from reflexlearn.learning.path_models import PathItemResource


def merge_resources(
    pinned: PathItemResource | None, auto: list[PathItemResource]
) -> list[PathItemResource]:
    """显式绑定资源置顶，concept 自动关联去重补充，最多 3 个。"""
    if pinned is None:
        return auto[:2]
    rest = [r for r in auto if r.resource_id != pinned.resource_id]
    return [pinned, *rest][:3]


async def resources_by_id(conn, resource_ids: list[str]) -> dict[str, PathItemResource]:
    """按 id 批量查资源（显式绑定），标 pinned=True。"""
    ids = [rid for rid in set(resource_ids) if rid]
    if not ids:
        return {}
    rows = await conn.fetch(
        """
        SELECT id::text AS resource_id, type,
               COALESCE(meta->>'title', type) AS title
        FROM resources WHERE id::text = ANY($1::text[])
        """,
        ids,
    )
    return {
        row["resource_id"]: PathItemResource(
            resource_id=row["resource_id"],
            title=str(row["title"] or ""),
            type=str(row["type"] or ""),
            pinned=True,
        )
        for row in rows
    }


async def resources_by_concept(
    conn, concepts: list[str], *, user_id: str, tenant_id: str
) -> dict[str, list[PathItemResource]]:
    """按 concept 批量查资源，每 concept 取前 2 个（created_at 倒序）。"""
    if not concepts:
        return {}
    rows = await conn.fetch(
        """
        SELECT id::text AS resource_id, concept, type,
               COALESCE(meta->>'title', type) AS title, created_at
        FROM resources
        WHERE user_id=$1 AND tenant_id=$2 AND concept = ANY($3::text[])
        ORDER BY created_at DESC
        """,
        user_id,
        tenant_id,
        list(set(concepts)),
    )
    grouped: dict[str, list[PathItemResource]] = {}
    for row in rows:
        bucket = grouped.setdefault(str(row["concept"]), [])
        if len(bucket) < 2:
            bucket.append(
                PathItemResource(
                    resource_id=row["resource_id"],
                    title=str(row["title"] or ""),
                    type=str(row["type"] or ""),
                )
            )
    return grouped
