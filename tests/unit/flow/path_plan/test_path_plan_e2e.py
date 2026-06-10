from __future__ import annotations

import json

import pytest

from reflexlearn.common.config import get_settings
from reflexlearn.llm_gateway.gateway import Completion


class _IntegrationLLM:
    """planner→2 任务；path_plan→抛错走规则；其余返回长文本通过规则质量校验。"""

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        sys = messages[0]["content"] if messages else ""
        if "路径规划" in sys:
            raise RuntimeError("force-rule-for-deterministic-path")
        if task_type == "planning":
            return Completion(
                text=json.dumps(
                    {
                        "tasks": [
                            {
                                "type": "doc",
                                "concept_ids": ["c1"],
                                "difficulty": 0.4,
                                "style_hint": "active",
                                "constraints": [],
                            },
                            {
                                "type": "quiz",
                                "concept_ids": ["c2"],
                                "difficulty": 0.6,
                                "style_hint": "active",
                                "constraints": [],
                            },
                        ]
                    },
                    ensure_ascii=False,
                )
            )
        return Completion(
            text=(
                "这是一段足够长的机器学习教学内容，用于通过基于长度的质量校验规则，"
                "并作为下游节点的上下文输入。内容涵盖线性回归的基本概念、损失函数定义，"
                "以及最小二乘法求解参数的完整推导步骤与数值示例。"
            )
        )


@pytest.mark.asyncio
async def test_build_graph_assemble_to_path_plan_to_end():
    frames = await _run_graph_frames()

    assert "assemble" in frames["_seen"]
    assert "path_plan" in frames["_seen"]

    path = frames["path_plan"]["learning_path"]
    assert len(path) >= 2
    assert [s["sequence"] for s in path] == list(range(1, len(path) + 1))
    assert all(s.get("objective") for s in path)
    assert frames["assemble"]["resource_bundle"]["total"] >= 2


@pytest.mark.asyncio
async def test_path_plan_enriches_over_assemble_simple_path():
    frames = await _run_graph_frames()

    assemble_path = frames["assemble"]["learning_path"]
    pp_path = frames["path_plan"]["learning_path"]

    assert all("objective" not in p for p in assemble_path)
    assert pp_path[0].get("objective")


@pytest.mark.asyncio
async def test_eval_skip_path_plan_uses_simple_path(monkeypatch):
    monkeypatch.setenv("EVAL_SKIP_PATH_PLAN", "true")
    get_settings.cache_clear()

    try:
        frames = await _run_graph_frames()
    finally:
        get_settings.cache_clear()

    path = frames["path_plan"]["learning_path"]
    assert path == frames["assemble"]["learning_path"]
    assert all("objective" not in p for p in path)


async def _run_graph_frames() -> dict:
    from reflexlearn.orchestration.graph import build_graph

    graph = build_graph(_IntegrationLLM())
    frames: dict = {}
    seen: list[str] = []
    async for event in graph.astream(_e2e_initial(), stream_mode="updates"):
        for node_name, output in event.items():
            seen.append(node_name)
            frames[node_name] = output
    frames["_seen"] = seen
    return frames


def _e2e_initial() -> dict:
    return {
        "user_id": "u1",
        "acl": {"user_id": "u1"},
        "messages": [{"role": "user", "content": "线性回归基础"}],
        "learner_profile": {},
        "learning_goal": "线性回归基础",
        "collab_mode": "central",
        "resource_type_hints": [],
        "plan": [],
        "completed": [],
        "reflections": [],
        "iteration": 0,
        "replan_count": 0,
        "token_used": 0,
        "halt_reason": None,
        "conflict": None,
        "debate_rounds": None,
        "debate_verdict": None,
        "resource_bundle": None,
        "learning_path": None,
        "path_summary": None,
        "path_strategy": None,
    }
