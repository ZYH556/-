from __future__ import annotations

import pytest

from reflexlearn.orchestration.nodes.assemble import assemble_node


@pytest.mark.asyncio
async def test_assemble_produces_bundle_and_simple_path():
    """锁定 assemble 的 fallback 契约：bundle + 简单序号路径。

    path_plan 节点在不可达 / skill 失败时依赖 assemble 的这条简单路径作为最后兜底，
    本测试把该隐性契约显性化，防止将来误删破坏纵深防御。"""
    state = {
        "learning_goal": "线性回归",
        "learner_profile": {"cognitive_style": "visual", "weak_points": ["过拟合"]},
        "completed": [
            {"task_id": "t1", "status": "passed", "type": "doc", "content": "a"},
            {"task_id": "t2", "status": "passed", "type": "quiz", "content": "b"},
            {"task_id": "t3", "status": "failed", "type": "code", "issues": ["x"]},
        ],
    }

    res = await assemble_node(state)

    bundle = res["resource_bundle"]
    assert bundle["goal"] == "线性回归"
    assert bundle["total"] == 2  # 只统计 passed
    assert {r["task_id"] for r in bundle["resources"]} == {"t1", "t2"}
    assert bundle["profile_summary"]["cognitive_style"] == "visual"
    assert bundle["profile_summary"]["weak_points"] == ["过拟合"]

    path = res["learning_path"]
    assert [p["sequence"] for p in path] == [1, 2]
    assert all(set(p.keys()) == {"sequence", "resource_type", "task_id"} for p in path)
    assert all("objective" not in p for p in path)


@pytest.mark.asyncio
async def test_assemble_empty_completed_yields_empty():
    res = await assemble_node({"learning_goal": "g", "learner_profile": {}, "completed": []})
    assert res["resource_bundle"]["total"] == 0
    assert res["learning_path"] == []
