"""学习画像聚合：把分散在 Redis / PG 的画像信号汇成一个可展示的档案。

维度对齐 docs/21 §10（≥6 维）：学习目标、知识基础、薄弱点、学习风格、
偏好、进度，外加错题模式与学习资产统计。任一数据源不可用都降级跳过，
绝不让画像接口 500。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.profile_history import (
    ProfileTrend,
    load_profile_history,
    save_profile_snapshot,
)
from reflexlearn.memory import session_store

logger = logging.getLogger(__name__)
router = APIRouter()


class MistakeStats(BaseModel):
    total: int = 0
    open: int = 0
    top_concepts: list[str] = Field(default_factory=list)


class StudyStats(BaseModel):
    """资源学习状态统计：行为回流的画像侧出口（喂 /growth 与快照趋势）。"""

    total: int = 0
    in_progress: int = 0
    done: int = 0
    reviewed: int = 0


class ProfileSummary(BaseModel):
    user_id: str
    goal: str = ""
    knowledge_base: dict[str, float] = Field(default_factory=dict)
    weak_points: list[str] = Field(default_factory=list)
    cognitive_style: str = "active"
    preferences: dict = Field(default_factory=dict)
    progress: float = 0.0
    mistake_stats: MistakeStats = Field(default_factory=MistakeStats)
    study_stats: StudyStats = Field(default_factory=StudyStats)
    spaces_count: int = 0
    resources_count: int = 0
    source: str = "empty"
    degraded: list[str] = Field(default_factory=list)


@router.get("/profile")
async def get_profile(user: CurrentUser = Depends(get_current_user)) -> ProfileSummary:
    summary = ProfileSummary(user_id=user.user_id)

    profile = await session_store.load_profile(user.user_id, tenant_id=user.tenant_id)
    if profile:
        summary.source = "redis"

    pg_pool = await safe_pg_pool()
    if not profile and pg_pool is not None:
        profile = await _profile_from_pg(user.user_id, pg_pool)
        if profile:
            summary.source = "pg"

    if profile:
        summary.goal = str(profile.get("goal", ""))
        kb = profile.get("knowledge_base", {})
        if isinstance(kb, dict):
            summary.knowledge_base = {
                str(k): float(v) for k, v in kb.items() if isinstance(v, (int, float))
            }
        weak = profile.get("weak_points", [])
        if isinstance(weak, list):
            summary.weak_points = [str(w) for w in weak][:8]
        summary.cognitive_style = str(profile.get("cognitive_style", "active"))
        prefs = profile.get("preferences", {})
        if isinstance(prefs, dict):
            summary.preferences = prefs
        try:
            summary.progress = float(profile.get("progress", 0.0))
        except (TypeError, ValueError):
            summary.progress = 0.0

    if pg_pool is not None:
        await _attach_pg_stats(summary, user, pg_pool)
        if profile:
            # 快照内容 = 画像 + 行为统计：学习状态变化也会推动新快照（趋势数据源）
            snapshot_payload = dict(profile)
            snapshot_payload["study_stats"] = summary.study_stats.model_dump()
            await save_profile_snapshot(user.user_id, snapshot_payload, pg_pool)
    else:
        summary.degraded.append("pg:unavailable")
    return summary


@router.get("/profile/history")
async def get_profile_history(user: CurrentUser = Depends(get_current_user)) -> ProfileTrend:
    pg_pool = await safe_pg_pool()
    return await load_profile_history(user.user_id, pg_pool)


async def _profile_from_pg(user_id: str, pg_pool) -> dict | None:
    try:
        async with pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT dimensions FROM learner_profiles
                WHERE user_id=$1 ORDER BY version DESC, updated_at DESC LIMIT 1
                """,
                user_id,
            )
        if row and row["dimensions"]:
            import json

            raw = row["dimensions"]
            return raw if isinstance(raw, dict) else json.loads(raw)
    except Exception as exc:
        logger.info("profile pg degraded: %s", exc)
    return None


async def _attach_pg_stats(summary: ProfileSummary, user: CurrentUser, pg_pool) -> None:
    try:
        async with pg_pool.acquire() as conn:
            mistake_rows = await conn.fetch(
                """
                SELECT concept, status FROM mistakes
                WHERE tenant_id=$1 AND user_id=$2
                ORDER BY created_at DESC LIMIT 200
                """,
                user.tenant_id,
                user.user_id,
            )
            spaces = await conn.fetchval(
                "SELECT COUNT(*) FROM learning_goals WHERE user_id=$1 AND tenant_id=$2",
                user.user_id,
                user.tenant_id,
            )
            resources = await conn.fetchval(
                "SELECT COUNT(*) FROM resources WHERE user_id=$1 AND tenant_id=$2",
                user.user_id,
                user.tenant_id,
            )
            study_rows = await conn.fetch(
                """
                SELECT COALESCE(study_status, 'unread') AS study_status, COUNT(*) AS n
                FROM resources WHERE user_id=$1 AND tenant_id=$2
                GROUP BY 1
                """,
                user.user_id,
                user.tenant_id,
            )
        concept_count: dict[str, int] = {}
        open_count = 0
        for row in mistake_rows:
            concept = (row["concept"] or "").strip()
            if concept:
                concept_count[concept] = concept_count.get(concept, 0) + 1
            if row["status"] == "open":
                open_count += 1
        summary.mistake_stats = MistakeStats(
            total=len(mistake_rows),
            open=open_count,
            top_concepts=[
                c for c, _ in sorted(concept_count.items(), key=lambda kv: -kv[1])[:3]
            ],
        )
        summary.spaces_count = int(spaces or 0)
        summary.resources_count = int(resources or 0)
        counts = {row["study_status"]: int(row["n"]) for row in study_rows}
        summary.study_stats = StudyStats(
            total=sum(counts.values()),
            in_progress=counts.get("in_progress", 0),
            done=counts.get("done", 0),
            reviewed=counts.get("reviewed", 0),
        )
    except Exception as exc:
        logger.info("profile stats degraded: %s", exc)
        summary.degraded.append("pg:stats_unavailable")
