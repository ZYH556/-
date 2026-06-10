from __future__ import annotations

import json

import pytest

from reflexlearn.common.config import get_settings


class _E2EFakeLLM:
    """planning 返回 2 任务 + collab_mode=pipeline；其余返回足够长文本通过规则质量检查。"""

    def __init__(self):
        self.task_types: list[str] = []

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        from reflexlearn.llm_gateway.gateway import Completion

        self.task_types.append(task_type)
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
                                "difficulty": 0.5,
                                "style_hint": "active",
                                "constraints": [],
                            },
                        ],
                        "collab_mode": "pipeline",
                    },
                    ensure_ascii=False,
                )
            )
        return Completion(
            text=(
                "ML teaching content long enough to pass the length-based rule quality check "
                "and serve as downstream context."
            )
        )


@pytest.mark.asyncio
async def test_pipeline_end_to_end_reachable():
    """astream 从 START 应真正走到 pipeline 节点并产出资源包。"""
    from reflexlearn.orchestration.graph import build_graph

    graph = build_graph(_E2EFakeLLM())
    seen, final = await _run_graph(graph)

    assert "pipeline" in seen
    assert "debate" not in seen
    assert final["resource_bundle"]["total"] == 2


@pytest.mark.asyncio
async def test_build_graph_can_disable_llm_quality_check(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_QUALITY_CHECK", "false")
    get_settings.cache_clear()
    llm = _E2EFakeLLM()

    try:
        from reflexlearn.orchestration.graph import build_graph

        graph = build_graph(llm)
        seen, final = await _run_graph(graph)
    finally:
        get_settings.cache_clear()

    assert "pipeline" in seen
    assert final["resource_bundle"]["total"] == 2
    assert "verification" not in llm.task_types


async def _run_graph(graph) -> tuple[list[str], dict]:
    initial = {
        "user_id": "u1",
        "acl": {"user_id": "u1"},
        "messages": [{"role": "user", "content": "ML path"}],
        "learner_profile": {},
        "learning_goal": "systematic learning path",
        "collab_mode": "central",
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
    }

    seen: list[str] = []
    final: dict = {}
    async for event in graph.astream(initial, stream_mode="updates"):
        for node_name, output in event.items():
            seen.append(node_name)
            if node_name == "assemble":
                final = output
    return seen, final
