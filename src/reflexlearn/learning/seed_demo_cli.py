from __future__ import annotations

import argparse
import asyncio
import json

import asyncpg

from reflexlearn.common.config import get_settings
from reflexlearn.learning.demo_seed import (
    DemoProfile,
    DemoResource,
    DemoSeed,
    DemoSpace,
    build_demo_seed,
)


async def seed_learning_product(*, user_id: str, tenant_id: str) -> int:
    seed = build_demo_seed(user_id, tenant_id)
    dsn = get_settings().database_url
    try:
        conn = await asyncpg.connect(dsn=dsn)
    except Exception as exc:
        _print_degraded(seed, f"pg:connect_failed:{exc.__class__.__name__}")
        return 0
    try:
        async with conn.transaction():
            await _clean(conn, user_id=user_id, tenant_id=tenant_id)
            await _upsert_users(conn, seed.profiles, tenant_id)
            # space → 真实资源概念映射：让路径节点 concept 与资源 concept 对齐，
            # 使「节点关联资源」（path_ops 按 concept 匹配）能命中。
            space_concepts: dict[str, list[str]] = {}
            for res in seed.resources:
                bucket = space_concepts.setdefault(res.space_id, [])
                if res.concept and res.concept not in bucket:
                    bucket.append(res.concept)
            goal_ids = await _insert_spaces(conn, seed.spaces, space_concepts)
            await _insert_profiles(conn, seed.profiles)
            await _insert_resources(conn, seed, goal_ids)
            await _insert_mistakes(conn, seed)
        _print_ok(seed)
    except Exception as exc:
        _print_degraded(seed, f"pg:write_failed:{exc.__class__.__name__}")
        return 0
    finally:
        await conn.close()
    return 0


async def _clean(conn: asyncpg.Connection, *, user_id: str, tenant_id: str) -> None:
    await conn.execute(
        """
        DELETE FROM path_items WHERE path_id IN (
            SELECT lp.id FROM learning_paths lp
            JOIN learning_goals lg ON lg.id = lp.goal_id
            WHERE lg.course='product-seed' AND lg.user_id=$1 AND lg.tenant_id=$2)
        """,
        user_id,
        tenant_id,
    )
    await conn.execute(
        """
        DELETE FROM learning_paths WHERE goal_id IN (
            SELECT id FROM learning_goals
            WHERE course='product-seed' AND user_id=$1 AND tenant_id=$2)
        """,
        user_id,
        tenant_id,
    )
    await conn.execute(
        "DELETE FROM resources WHERE user_id=$1 AND tenant_id=$2 AND meta->>'seed_kind'='product'",
        user_id,
        tenant_id,
    )
    await conn.execute(
        "DELETE FROM learning_goals WHERE course='product-seed' AND user_id=$1 AND tenant_id=$2",
        user_id,
        tenant_id,
    )
    await conn.execute(
        "DELETE FROM mistakes WHERE user_id=$1 AND tenant_id=$2 AND mistake_id LIKE 'seed-mistake-%'",
        user_id,
        tenant_id,
    )
    await conn.execute(
        "DELETE FROM learner_profiles WHERE user_id IN ($1, 'student-frontend', 'student-math')",
        user_id,
    )


async def _upsert_users(
    conn: asyncpg.Connection, profiles: list[DemoProfile], tenant_id: str
) -> None:
    for profile in profiles:
        await conn.execute(
            """
            INSERT INTO users (id, role, tenant_id, password_hash)
            VALUES ($1, 'student', $2, '')
            ON CONFLICT (id) DO UPDATE SET tenant_id=EXCLUDED.tenant_id
            """,
            profile.user_id,
            tenant_id,
        )


async def _insert_spaces(
    conn: asyncpg.Connection,
    spaces: list[DemoSpace],
    space_concepts: dict[str, list[str]],
) -> dict[str, int]:
    goal_ids: dict[str, int] = {}
    for space in spaces:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_goals (user_id, tenant_id, course, goal_text, status, progress)
            VALUES ($1, $2, 'product-seed', $3, $4, $5)
            RETURNING id
            """,
            space.user_id,
            space.tenant_id,
            space.title,
            space.status,
            space.progress,
        )
        goal_ids[space.space_id] = int(row["id"])
        await _insert_path(conn, space, int(row["id"]), space_concepts.get(space.space_id, []))
    return goal_ids


async def _insert_path(
    conn: asyncpg.Connection,
    space: DemoSpace,
    goal_id: int,
    concepts: list[str],
) -> None:
    path = await conn.fetchrow(
        """
        INSERT INTO learning_paths (user_id, tenant_id, goal_id, summary, strategy)
        VALUES ($1, $2, $3, $4, 'profile_weakness_first') RETURNING id
        """,
        space.user_id,
        space.tenant_id,
        goal_id,
        f"围绕“{space.title}”按薄弱点优先推进。",
    )
    # 路径三步用该 space 真实资源概念（对齐资源匹配）；不足时补教学法泛步
    fallback = ["建立直觉", "补齐卡点", "短练巩固"]
    steps = (concepts[:3] + fallback)[:3] if concepts else fallback
    for idx, concept in enumerate(steps, start=1):
        await conn.execute(
            """
            INSERT INTO path_items (
                path_id, sequence, task_ref, resource_type, concept,
                objective, rationale, difficulty, mastery_status
            )
            VALUES ($1, $2, $3, 'ai_document', $4, $5, $6, $7, $8)
            """,
            path["id"],
            idx,
            f"{space.space_id}-step-{idx}",
            concept,
            f"{space.title}：{concept}",
            "根据画像与错题记录安排下一步。",
            0.2 + idx * 0.15,
            "done" if idx == 1 and space.progress > 0.5 else "not_started",
        )


async def _insert_profiles(conn: asyncpg.Connection, profiles: list[DemoProfile]) -> None:
    for profile in profiles:
        await conn.execute(
            """
            INSERT INTO learner_profiles (user_id, dimensions, version)
            VALUES ($1, $2::jsonb, 1)
            """,
            profile.user_id,
            json.dumps(_profile_dimensions(profile), ensure_ascii=False),
        )


async def _insert_resources(
    conn: asyncpg.Connection, seed: DemoSeed, goal_ids: dict[str, int]
) -> None:
    for resource in seed.resources:
        await conn.execute(
            """
            INSERT INTO resources (
                goal_id, type, content, meta, quality_score,
                user_id, tenant_id, visibility, concept
            )
            VALUES ($1, $2, $3, $4::jsonb, 0.86, $5, $6, 'private', $7)
            """,
            goal_ids.get(resource.space_id),
            resource.type,
            resource.content,
            json.dumps(_resource_meta(resource), ensure_ascii=False),
            resource.user_id,
            resource.tenant_id,
            resource.concept,
        )


async def _insert_mistakes(conn: asyncpg.Connection, seed: DemoSeed) -> None:
    for mistake in seed.mistakes:
        await conn.execute(
            """
            INSERT INTO mistakes (
                mistake_id, user_id, tenant_id, question, answer,
                expected, concept, source_resource_id, status, analysis
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, '{}'::jsonb)
            """,
            mistake.mistake_id,
            mistake.user_id,
            mistake.tenant_id,
            mistake.question,
            mistake.answer,
            mistake.expected,
            mistake.concept,
            mistake.source_resource_id,
            mistake.status,
        )


def _profile_dimensions(profile: DemoProfile) -> dict[str, object]:
    return {
        "goal": profile.goal,
        "weak_points": profile.weak_points,
        "preferences": profile.preferences,
        "progress": profile.progress,
        "cognitive_style": profile.cognitive_style,
        "knowledge_base": profile.knowledge_base,
    }


def _resource_meta(resource: DemoResource) -> dict[str, object]:
    return {
        "seed_kind": "product",
        "title": resource.title,
        "provider": resource.provider,
        "source_label": resource.source_label,
        "estimated_minutes": resource.estimated_minutes,
        "reason": resource.reason,
        "href": resource.href,
        "embed_url": resource.embed_url,
        "usage_mode": resource.usage_mode,
        "source_policy": resource.source_policy,
    }


def _print_ok(seed: DemoSeed) -> None:
    print("product_seed -> ok")
    _print_counts(seed)


def _print_degraded(seed: DemoSeed, reason: str) -> None:
    print(f"product_seed -> degraded ({reason})")
    print("product_seed -> generated structured data only; database write skipped")
    _print_counts(seed)


def _print_counts(seed: DemoSeed) -> None:
    print(f"  - spaces   : {len(seed.spaces)}")
    print(f"  - resources: {len(seed.resources)}")
    print(f"  - mistakes : {len(seed.mistakes)}")
    print(f"  - profiles : {len(seed.profiles)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", default="admin")
    parser.add_argument("--tenant-id", default="default")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(seed_learning_product(user_id=args.user_id, tenant_id=args.tenant_id)))


if __name__ == "__main__":
    main()
