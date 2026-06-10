"""path_plan 节点：agent 主链路最后一环（assemble → path_plan → END）。

从 completed 取通过的资源，按 task_id join plan[].spec 补回 concept/difficulty
（completed item 只带 type/content），交给 path_plan Skill 排成个性化学习路径，
写入 learning_path（非 reducer 字段，覆盖 assemble 写的简单兜底路径）。

降级纵深：无 passed 资源 / 无 path_plan skill / skill 未产出 → 回退 _simple_fallback
（结构与 assemble 一致，保证 learning_path 永不为空）。本节点不自增 iteration
（与 assemble 一致；多加会把 iteration 推近 max_iterations，反而增加自身被 harness 闸门跳过的概率）。
"""
from __future__ import annotations

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.state import AgentState
from reflexlearn.skills.base import SkillContext


async def _load_concept_graph(acl: dict) -> dict | None:
    """查 Neo4j 全量 PREREQUISITE_OF，构建 {concept: [prereq_concepts]}。
    Neo4j 未装 / 连不上 / 无数据 → None（path_plan skill 退启发式排序）。ACL 在 Cypher WHERE 注入。"""
    try:
        from reflexlearn.common.db import get_neo4j

        driver = get_neo4j()
        tid = acl.get("tenant_id", "default")
        cypher = (
            "MATCH (a:Concept)-[:PREREQUISITE_OF]->(b:Concept) "
            "WHERE (a.tenant_id=$tid OR a.visibility='public') "
            "  AND (b.tenant_id=$tid OR b.visibility='public') "
            "RETURN a.name AS prereq, b.name AS concept"
        )
        async with driver.session() as s:
            rec = await s.run(cypher, tid=tid)
            rows = [r.data() async for r in rec]
        graph: dict[str, list[str]] = {}
        for r in rows:
            graph.setdefault(r["concept"], []).append(r["prereq"])
        return graph or None
    except Exception:
        return None


def _flatten(c: dict, plan_by_id: dict, goal: str) -> dict:
    """把 completed item 摊平成 path_plan skill 所需的扁平资源（含 concept/difficulty）。"""
    task_id = c.get("task_id", "")
    task = plan_by_id.get(task_id)
    if task:
        spec = task.get("spec", {}) or {}
        concept_ids = spec.get("concept_ids") or []
        concept = concept_ids[0] if concept_ids else (goal or "该主题")
        difficulty = spec.get("difficulty", 0.5)
    else:
        # debate-verdict 等不在 plan 的资源：用 winner_position / goal 兜底，绝不 KeyError
        concept = c.get("winner_position") or goal or "该主题"
        difficulty = 0.5
    try:
        difficulty = float(difficulty)
    except (TypeError, ValueError):
        difficulty = 0.5
    return {
        "task_id": task_id,
        "resource_type": c.get("type", "doc"),
        "concept": concept,
        "difficulty": difficulty,
    }


def _simple_fallback(passed: list[dict]) -> list[dict]:
    """与 assemble.py 的简单路径结构一致，作为 skill 不可用时的最后兜底。"""
    return [
        {"sequence": i + 1, "resource_type": r.get("type", "doc"), "task_id": r.get("task_id", "")}
        for i, r in enumerate(passed)
    ]


async def path_plan_node(state: AgentState) -> dict:
    completed = state.get("completed", [])
    passed = [c for c in completed if c.get("status") == "passed"]
    goal = state.get("learning_goal", "")
    plan_by_id = {t["task_id"]: t for t in state.get("plan", []) if t.get("task_id")}
    settings = get_settings()

    skill = state.get("_skills", {}).get("path_plan")
    if settings.eval_skip_path_plan or not passed or skill is None:
        return {"learning_path": _simple_fallback(passed), "path_summary": "", "path_strategy": ""}

    resources = [_flatten(c, plan_by_id, goal) for c in passed]
    ctx = SkillContext(
        user_id=state.get("user_id", "anonymous"),
        acl=state.get("acl", {}),
        task_id="path_plan",
    )
    # enable_graph_retrieval 开启时注入 Neo4j 真实概念依赖图（PREREQUISITE_OF→拓扑排序）；
    # 否则 graph=None，skill 走启发式排序（零回归）。加载失败同样退 None，降级安全。
    graph = None
    if settings.enable_graph_retrieval:
        graph = await _load_concept_graph(state.get("acl", {}))
    res = await skill.run(
        {
            "resources": resources,
            "profile": state.get("learner_profile", {}),
            "goal": goal,
            "graph": graph,
        },
        ctx,
    )
    if res.ok and res.data and res.data.get("path"):
        return {
            "learning_path": res.data["path"],
            "path_summary": res.data.get("summary", ""),
            "path_strategy": res.data.get("strategy", ""),
        }
    return {"learning_path": _simple_fallback(passed), "path_summary": "", "path_strategy": ""}
