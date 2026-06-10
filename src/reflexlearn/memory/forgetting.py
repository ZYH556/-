"""经验记忆主动遗忘：离线扫描低复用过期点并删除。

本模块只接收注入的 qdrant client，不自取外部依赖；所有异常降级为空跑。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from reflexlearn.memory.reflexion import EXPERIENCE_COLLECTION


async def run_forgetting_job(*, qdrant, settings, now_iso: str) -> int:
    """按配置执行遗忘作业；开关关闭或依赖不可用时空跑。"""
    if not bool(getattr(settings, "enable_forgetting", False)):
        return 0
    return await forget_stale(
        qdrant=qdrant,
        now_iso=now_iso,
        ttl_days=int(getattr(settings, "memory_ttl_days", 90)),
        min_hits=int(getattr(settings, "memory_forget_min_hits", 1)),
    )


async def forget_stale(*, qdrant, now_iso: str, ttl_days: int, min_hits: int) -> int:
    """删除 created_at 过期且 hit_count 低于阈值的经验点，返回删除数量。"""
    if qdrant is None:
        return 0

    now = _parse_iso(now_iso)
    if now is None:
        return 0

    ids: list[Any] = []
    offset = None
    while True:
        try:
            points, offset = await qdrant.scroll(
                collection_name=EXPERIENCE_COLLECTION,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            return 0
        ids.extend(_stale_ids(points, now=now, ttl_days=ttl_days, min_hits=min_hits))
        if offset is None:
            break

    if not ids:
        return 0
    try:
        await qdrant.delete(collection_name=EXPERIENCE_COLLECTION, points_selector=ids)
    except Exception:
        return 0
    return len(ids)


def _stale_ids(points: list, *, now: datetime, ttl_days: int, min_hits: int) -> list[Any]:
    cutoff = now - timedelta(days=max(0, ttl_days))
    stale: list[Any] = []
    for point in points or []:
        payload = getattr(point, "payload", None) or {}
        created_at = _parse_iso(str(payload.get("created_at") or ""))
        if created_at is None:
            continue
        hit_count = _as_int(payload.get("hit_count"), default=0)
        if created_at < cutoff and hit_count < min_hits:
            point_id = getattr(point, "id", None)
            if point_id is not None:
                stale.append(point_id)
    return stale


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _as_int(value, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
