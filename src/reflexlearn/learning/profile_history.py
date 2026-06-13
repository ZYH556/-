from __future__ import annotations

import json
import logging
from typing import Mapping

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProfileHistorySnapshot(BaseModel):
    version: int
    created_at: float
    goal: str = ""
    progress: float = 0.0
    weak_points: list[str] = Field(default_factory=list)
    knowledge_base: dict[str, float] = Field(default_factory=dict)
    completed_resources: int = 0  # done + reviewed，来自快照内嵌 study_stats


class ProfileTrend(BaseModel):
    items: list[ProfileHistorySnapshot] = Field(default_factory=list)
    start_progress: float = 0.0
    latest_progress: float = 0.0
    progress_delta: float = 0.0
    resolved_weak_points: list[str] = Field(default_factory=list)
    new_weak_points: list[str] = Field(default_factory=list)
    mastery_delta: dict[str, float] = Field(default_factory=dict)
    degraded: list[str] = Field(default_factory=list)


def build_profile_trend(items: list[ProfileHistorySnapshot]) -> ProfileTrend:
    ordered = sorted(items, key=lambda item: item.created_at)
    if not ordered:
        return ProfileTrend(degraded=["profile_history:empty"])

    first = ordered[0]
    latest = ordered[-1]
    first_weak = set(first.weak_points)
    latest_weak = set(latest.weak_points)
    all_concepts = set(first.knowledge_base) | set(latest.knowledge_base)
    mastery_delta = {
        concept: round(
            latest.knowledge_base.get(concept, 0.0) - first.knowledge_base.get(concept, 0.0),
            4,
        )
        for concept in sorted(all_concepts)
    }
    return ProfileTrend(
        items=ordered,
        start_progress=first.progress,
        latest_progress=latest.progress,
        progress_delta=round(latest.progress - first.progress, 4),
        resolved_weak_points=[point for point in first.weak_points if point not in latest_weak],
        new_weak_points=[point for point in latest.weak_points if point not in first_weak],
        mastery_delta=mastery_delta,
    )


async def load_profile_history(user_id: str, pg_pool, limit: int = 20) -> ProfileTrend:
    if pg_pool is None:
        return ProfileTrend(degraded=["pg:unavailable"])
    try:
        async with pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT version, dimensions, EXTRACT(EPOCH FROM created_at)::float AS created_at
                FROM profile_history
                WHERE user_id=$1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        snapshots = [_snapshot_from_row(row) for row in rows]
        return build_profile_trend(snapshots)
    except Exception as exc:
        logger.info("profile history degraded: %s", exc)
        return ProfileTrend(degraded=["pg:history_unavailable"])


async def save_profile_snapshot(user_id: str, profile: Mapping[str, object], pg_pool) -> None:
    if pg_pool is None or not profile:
        return
    try:
        async with pg_pool.acquire() as conn:
            latest = await conn.fetchrow(
                """
                SELECT dimensions FROM profile_history
                WHERE user_id=$1 ORDER BY created_at DESC LIMIT 1
                """,
                user_id,
            )
            # 画像内容没变就不写新快照：每次 GET /api/profile 都落一条会让
            # 趋势窗口（LIMIT 20）被同质快照灌满，跨时间趋势被挤出窗口。
            if latest is not None and _dimensions_equal(latest["dimensions"], profile):
                return
            version = await conn.fetchval(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM profile_history WHERE user_id=$1",
                user_id,
            )
            await conn.execute(
                """
                INSERT INTO profile_history (user_id, dimensions, version)
                VALUES ($1, $2::jsonb, $3)
                """,
                user_id,
                json.dumps(dict(profile), ensure_ascii=False),
                int(version or 1),
            )
    except Exception as exc:
        logger.info("profile snapshot skipped: %s", exc)


def _dimensions_equal(raw: object, profile: Mapping[str, object]) -> bool:
    try:
        existing = raw if isinstance(raw, dict) else json.loads(str(raw) or "{}")
        return existing == json.loads(json.dumps(dict(profile)))
    except Exception:
        return False


def _snapshot_from_row(row) -> ProfileHistorySnapshot:
    raw = row["dimensions"]
    dimensions = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    knowledge_base = dimensions.get("knowledge_base", {})
    weak_points = dimensions.get("weak_points", [])
    study_stats = dimensions.get("study_stats", {})
    completed = 0
    if isinstance(study_stats, dict):
        completed = int(study_stats.get("done", 0) or 0) + int(study_stats.get("reviewed", 0) or 0)
    return ProfileHistorySnapshot(
        version=int(row["version"] or 0),
        created_at=float(row["created_at"] or 0.0),
        goal=str(dimensions.get("goal", "")),
        progress=_float(dimensions.get("progress"), 0.0),
        weak_points=[str(item) for item in weak_points] if isinstance(weak_points, list) else [],
        completed_resources=completed,
        knowledge_base={
            str(key): float(value)
            for key, value in knowledge_base.items()
            if isinstance(value, (int, float))
        }
        if isinstance(knowledge_base, dict)
        else {},
    )


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
