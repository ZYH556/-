"""写入演示种子数据：学生画像样本 + 110+ 学习资源 + 空间/路径/错题。

幂等：seed 空间用 course='seed-demo' 标记、样本学生用 'seed-stu-' 前缀、
错题用 'seed-m-' 前缀，重跑先删后插。演示主账号挂 admin（开发默认账号）。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed_content import (  # noqa: E402
    CONCEPTS,
    build_all_resources,
    build_mistakes,
    build_student_profiles,
)

from reflexlearn.accounts.passwords import hash_password  # noqa: E402
from reflexlearn.common.config import get_settings  # noqa: E402

ADMIN = "admin"
TENANT = "default"
SEED_COURSE = "seed-demo"

# admin 的三个演示空间：标题 / 领域 / 进度
ADMIN_SPACES = [
    ("机器学习入门到实战", "机器学习", 0.35),
    ("Python 编程强化", "Python", 0.6),
    ("数据结构与算法基础", "数据结构", 0.1),
]

# 机器学习主路径的先修拓扑序
ML_ORDER = ["线性回归", "逻辑回归", "梯度下降", "过拟合与正则化", "K近邻",
            "聚类", "决策树", "支持向量机", "神经网络基础", "卷积神经网络"]


async def _clean(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        DELETE FROM path_items WHERE path_id IN (
            SELECT id FROM learning_paths WHERE goal_id IN (
                SELECT id FROM learning_goals WHERE course=$1))
        """,
        SEED_COURSE,
    )
    await conn.execute(
        "DELETE FROM learning_paths WHERE goal_id IN (SELECT id FROM learning_goals WHERE course=$1)",
        SEED_COURSE,
    )
    await conn.execute(
        "DELETE FROM resources WHERE goal_id IN (SELECT id FROM learning_goals WHERE course=$1)",
        SEED_COURSE,
    )
    await conn.execute("DELETE FROM learning_goals WHERE course=$1", SEED_COURSE)
    await conn.execute("DELETE FROM mistakes WHERE mistake_id LIKE 'seed-m-%'")
    await conn.execute("DELETE FROM learner_profiles WHERE user_id LIKE 'seed-stu-%' OR user_id=$1", ADMIN)
    await conn.execute("DELETE FROM users WHERE id LIKE 'seed-stu-%'")


async def _upsert_users(conn: asyncpg.Connection, profiles: list[dict]) -> None:
    admin_hash = hash_password("reflexlearn-admin", iterations=20_000)
    await conn.execute(
        """
        INSERT INTO users (id, role, tenant_id, password_hash)
        VALUES ($1, 'admin', $2, $3)
        ON CONFLICT (id) DO UPDATE SET password_hash=EXCLUDED.password_hash
        """,
        ADMIN,
        TENANT,
        admin_hash,
    )
    for p in profiles:
        await conn.execute(
            """
            INSERT INTO users (id, role, tenant_id, password_hash)
            VALUES ($1, 'student', $2, '') ON CONFLICT (id) DO NOTHING
            """,
            p["user_id"],
            TENANT,
        )


async def _insert_profiles(conn: asyncpg.Connection, profiles: list[dict]) -> int:
    admin_dimensions = {
        "goal": "机器学习入门到实战",
        "major": "计算机科学",
        "stage": "大三",
        "knowledge_base": {"线性回归": 0.7, "逻辑回归": 0.55, "梯度下降": 0.5,
                           "Python 函数": 0.8, "过拟合与正则化": 0.3},
        "weak_points": ["过拟合与正则化", "神经网络基础", "矩阵求导"],
        "cognitive_style": "active",
        "preferences": {"language": "zh", "prefer_code_examples": True},
        "progress": 0.35,
    }
    await conn.execute(
        "INSERT INTO learner_profiles (user_id, dimensions, version) VALUES ($1, $2::jsonb, 1)",
        ADMIN,
        json.dumps(admin_dimensions, ensure_ascii=False),
    )
    for p in profiles:
        await conn.execute(
            "INSERT INTO learner_profiles (user_id, dimensions, version) VALUES ($1, $2::jsonb, 1)",
            p["user_id"],
            json.dumps(p["dimensions"], ensure_ascii=False),
        )
    return len(profiles) + 1


async def _insert_spaces_and_paths(conn: asyncpg.Connection, profiles: list[dict]) -> dict:
    stats = {"spaces": 0, "paths": 0, "steps": 0}
    goal_ids: dict[str, int] = {}
    for title, domain, progress in ADMIN_SPACES:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_goals (user_id, tenant_id, course, goal_text, status, progress)
            VALUES ($1, $2, $3, $4, 'active', $5) RETURNING id
            """,
            ADMIN, TENANT, SEED_COURSE, title, progress,
        )
        goal_ids[domain] = row["id"]
        stats["spaces"] += 1

    by_name = {c["name"]: c for c in CONCEPTS}
    domain_orders = {
        "机器学习": ML_ORDER,
        "Python": [c["name"] for c in CONCEPTS if c["domain"] == "Python"],
        "数据结构": [c["name"] for c in CONCEPTS if c["domain"] == "数据结构"],
    }
    for domain, order in domain_orders.items():
        path = await conn.fetchrow(
            """
            INSERT INTO learning_paths (user_id, tenant_id, goal_id, summary, strategy)
            VALUES ($1, $2, $3, $4, 'pedagogy_rule') RETURNING id
            """,
            ADMIN, TENANT, goal_ids[domain],
            f"按先修关系由浅入深完成 {len(order)} 个核心概念",
        )
        stats["paths"] += 1
        progress = next(p for t, d, p in ADMIN_SPACES if d == domain)
        done_n = int(len(order) * progress)
        for i, name in enumerate(order):
            c = by_name[name]
            status = "done" if i < done_n else ("in_progress" if i == done_n else "not_started")
            await conn.execute(
                """
                INSERT INTO path_items (path_id, sequence, task_ref, resource_type, concept,
                                        objective, rationale, difficulty, mastery_status)
                VALUES ($1, $2, $3, 'doc', $4, $5, $6, $7, $8)
                """,
                path["id"], i + 1, f"seed-{domain}-{i + 1}", name,
                f"掌握：{c['points'][0]}",
                f"先修「{c['prereq']}」已就绪，按教学序进入本概念" if c["prereq"] else "零基础友好的起点概念",
                c["difficulty"], status,
            )
            stats["steps"] += 1

    # 7 个样本学生空间 + 3 步短路径（凑满 10 条路径样例）
    for p in profiles[:7]:
        row = await conn.fetchrow(
            """
            INSERT INTO learning_goals (user_id, tenant_id, course, goal_text, status, progress)
            VALUES ($1, $2, $3, $4, 'active', $5) RETURNING id
            """,
            p["user_id"], TENANT, SEED_COURSE,
            p["dimensions"]["goal"], p["dimensions"]["progress"],
        )
        stats["spaces"] += 1
        path = await conn.fetchrow(
            """
            INSERT INTO learning_paths (user_id, tenant_id, goal_id, summary, strategy)
            VALUES ($1, $2, $3, '针对薄弱点的三步补救路径', 'weakness_first') RETURNING id
            """,
            p["user_id"], TENANT, row["id"],
        )
        stats["paths"] += 1
        for i, name in enumerate(p["dimensions"]["weak_points"][:3] or ["线性回归"]):
            c = by_name.get(name, CONCEPTS[0])
            await conn.execute(
                """
                INSERT INTO path_items (path_id, sequence, task_ref, resource_type, concept,
                                        objective, rationale, difficulty, mastery_status)
                VALUES ($1, $2, $3, 'doc', $4, $5, '画像薄弱点优先补强', $6, 'not_started')
                """,
                path["id"], i + 1, f"seed-{p['user_id']}-{i + 1}",
                c["name"], f"补弱：{c['points'][0]}", c["difficulty"],
            )
            stats["steps"] += 1
    return {"goal_ids": goal_ids, **stats}


async def _insert_resources(conn: asyncpg.Connection, goal_ids: dict) -> int:
    count = 0
    for res in build_all_resources():
        goal_id = goal_ids.get(res["domain"])
        await conn.execute(
            """
            INSERT INTO resources (goal_id, type, content, meta, quality_score,
                                   user_id, tenant_id, visibility, concept)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, 'private', $8)
            """,
            goal_id, res["type"], res["content"],
            json.dumps({"title": res["title"], "seed": True, "domain": res["domain"]},
                       ensure_ascii=False),
            0.8, ADMIN, TENANT, res["concept"],
        )
        count += 1
    return count


async def _insert_mistakes(conn: asyncpg.Connection) -> int:
    items = build_mistakes(ADMIN)
    for m in items:
        await conn.execute(
            """
            INSERT INTO mistakes (mistake_id, user_id, tenant_id, question, answer,
                                  expected, concept, status, analysis)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, '{}'::jsonb)
            """,
            m["mistake_id"], m["user_id"], TENANT, m["question"], m["answer"],
            m["expected"], m["concept"], m["status"],
        )
    return len(items)


async def main() -> None:
    dsn = get_settings().database_url
    conn = await asyncpg.connect(dsn=dsn)
    try:
        profiles = build_student_profiles()
        async with conn.transaction():
            await _clean(conn)
            await _upsert_users(conn, profiles)
            n_profiles = await _insert_profiles(conn, profiles)
            space_stats = await _insert_spaces_and_paths(conn, profiles)
            n_resources = await _insert_resources(conn, space_stats["goal_ids"])
            n_mistakes = await _insert_mistakes(conn)
        print("[OK] seed completed:")
        print(f"  - learner profiles : {n_profiles}")
        print(f"  - learning spaces  : {space_stats['spaces']}")
        print(f"  - learning paths   : {space_stats['paths']} (steps={space_stats['steps']})")
        print(f"  - resources        : {n_resources}")
        print(f"  - mistakes         : {n_mistakes}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
