from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.graph import build_graph


class _GraphLLM:
    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        if task_type == "profiling":
            return Completion(
                text=json.dumps(
                    {
                        "knowledge_base": {},
                        "cognitive_style": "active",
                        "goal": "学习线性回归",
                        "weak_points": [],
                        "preferences": {},
                        "progress": 0.0,
                    },
                    ensure_ascii=False,
                )
            )
        if task_type == "planning":
            return Completion(
                text=json.dumps(
                    {
                        "tasks": [
                            {
                                "type": "doc",
                                "concept_ids": ["linear_regression"],
                                "difficulty": 0.4,
                                "style_hint": "active",
                                "constraints": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            )
        if task_type == "reasoning":
            return Completion(
                text=json.dumps(
                    {
                        "score": 0.4,
                        "issues": ["示例不足"],
                        "refine_hint": "补充梯度下降例子",
                        "suggested_skill": "doc_gen",
                    },
                    ensure_ascii=False,
                )
            )
        return Completion(text="ML teaching content long enough to pass rule quality check.")


@pytest.mark.asyncio
async def test_enabled_graph_routes_through_metacognition(monkeypatch):
    monkeypatch.setenv("ENABLE_METACOGNITION", "true")
    monkeypatch.setenv("ENABLE_LLM_QUALITY_CHECK", "false")
    from reflexlearn.common.config import get_settings

    get_settings.cache_clear()
    try:
        graph = build_graph(_GraphLLM())
        seen = []
        async for event in graph.astream(_initial_state(), stream_mode="updates"):
            seen.extend(event.keys())
            if seen.count("generate_resource") >= 2:
                break
    finally:
        get_settings.cache_clear()

    assert "metacognition" in seen
    assert seen.count("generate_resource") >= 2


def _initial_state() -> dict:
    return {
        "user_id": "u1",
        "session_id": "sid",
        "acl": {"user_id": "u1"},
        "messages": [{"role": "user", "content": "线性回归"}],
        "summary_layers": [],
        "learner_profile": {},
        "learning_goal": "线性回归",
        "collab_mode": "central",
        "resource_type_hints": [],
        "plan": [],
        "completed": [],
        "reflections": [],
        "iteration": 0,
        "replan_count": 0,
        "self_refine_count": 0,
        "meta_reviews": [],
        "token_used": 0,
        "halt_reason": None,
        "conflict": None,
        "debate_rounds": None,
        "debate_verdict": None,
        "resource_bundle": None,
        "learning_path": None,
    }
