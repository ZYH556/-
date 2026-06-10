from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.nodes.collaboration.debate import debate_node, judge_node


class FakeLLM:
    def __init__(self, judge_payload: dict | None = None):
        self.judge_payload = judge_payload or {
            "winner_position": "正方",
            "reasoning": "正方证据更充分",
            "confidence": 0.8,
        }
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if kwargs.get("schema"):
            return Completion(text=json.dumps(self.judge_payload, ensure_ascii=False))
        return Completion(
            text=json.dumps(
                {
                    "perspective": "debater",
                    "claim": "线性回归适合解释连续目标变量",
                    "evidence_summary": "证据摘要",
                    "confidence": 0.7,
                },
                ensure_ascii=False,
            )
        )


def base_state(llm=None) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {},
        "learning_goal": "判断线性回归适用场景",
        "plan": [],
        "completed": [],
        "reflections": [],
        "iteration": 0,
        "replan_count": 0,
        "token_used": 0,
        "halt_reason": None,
        "conflict": {
            "has_conflict": True,
            "chunks": [
                {"source": "a", "content": "适合连续目标变量", "relevance_score": 0.8},
                {"source": "b", "content": "分类任务也可直接使用", "relevance_score": 0.4},
            ],
        },
        "debate_rounds": None,
        "debate_verdict": None,
        "resource_bundle": None,
        "learning_path": None,
        "_llm": llm,
    }


@pytest.mark.asyncio
async def test_debate_node_runs_parallel_positions_with_fallback():
    result = await debate_node(base_state())

    assert len(result["debate_rounds"]) >= 1
    assert len(result["debate_rounds"][0]["positions"]) == 2
    assert result["debate_rounds"][0]["positions"][0]["perspective"] == "a"


@pytest.mark.asyncio
async def test_judge_node_uses_llm_verdict():
    state = base_state(FakeLLM())
    state["debate_rounds"] = [
        {
            "round": 1,
            "positions": [
                {"perspective": "a", "claim": "正方", "confidence": 0.8},
                {"perspective": "b", "claim": "反方", "confidence": 0.4},
            ],
        }
    ]

    result = await judge_node(state)

    assert result["debate_verdict"]["winner_position"] == "正方"
    assert result["debate_verdict"]["confidence"] == 0.8
    verdict_resource = result["completed"][0]
    assert verdict_resource["status"] == "passed"
    assert verdict_resource["type"] == "debate"
    assert verdict_resource["confidence"] == 0.8
    assert state["_llm"].calls[0]["kwargs"]["task_type"] == "reasoning"


@pytest.mark.asyncio
async def test_judge_node_falls_back_without_llm():
    state = base_state()
    state["debate_rounds"] = [
        {
            "round": 1,
            "positions": [
                {"perspective": "a", "claim": "高置信观点", "confidence": 0.9},
                {"perspective": "b", "claim": "低置信观点", "confidence": 0.2},
            ],
        }
    ]

    result = await judge_node(state)

    assert result["debate_verdict"]["winner_position"] == "高置信观点"
    verdict_resource = result["completed"][0]
    assert verdict_resource["task_id"] == "debate-verdict"
    assert verdict_resource["status"] == "passed"


@pytest.mark.asyncio
async def test_judge_fallback_clamps_out_of_range_confidence():
    """confidence 越界时 fallback 不应抛 ValidationError，应 clamp 到 [0, 1]。"""
    state = base_state()
    state["debate_rounds"] = [
        {
            "round": 1,
            "positions": [
                {"perspective": "a", "claim": "越界观点", "confidence": 1.8},
            ],
        }
    ]

    result = await judge_node(state)

    assert 0.0 <= result["debate_verdict"]["confidence"] <= 1.0
    assert result["debate_verdict"]["winner_position"] == "越界观点"


@pytest.mark.asyncio
async def test_debate_fallback_position_clamps_relevance_score():
    """relevance_score 越界时 fallback position 的 confidence 也应被 clamp。"""
    state = base_state()
    state["conflict"]["chunks"] = [
        {"source": "x", "content": "越界相关度", "relevance_score": 2.5},
    ]

    result = await debate_node(state)

    conf = result["debate_rounds"][0]["positions"][0]["confidence"]
    assert 0.0 <= conf <= 1.0


class _E2EDebateLLM:
    """planning 返回 5 任务（不显式 collab_mode，靠 goal 辩论关键词点火）；
    schema 调用返回裁决 JSON（judge 用得上；verification 解析失败由 rule_check 兜底 passed）；
    非 schema 返回长文本（资源生成 content；debater 解析失败走 _fallback_position 用注入的 chunks）。"""

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        if task_type == "planning":
            return Completion(
                text=json.dumps(
                    {
                        "tasks": [
                            {"type": t, "concept_ids": [f"c{i}"], "difficulty": 0.4, "style_hint": "active", "constraints": []}
                            for i, t in enumerate(["doc", "mindmap", "quiz", "code", "reading"])
                        ]
                    },
                    ensure_ascii=False,
                )
            )
        if schema is not None:
            return Completion(
                text=json.dumps(
                    {
                        "winner_position": "需视场景而定",
                        "reasoning": "正反方各有边界条件，建议结合数据规模与任务类型权衡后再决定。",
                        "confidence": 0.6,
                    },
                    ensure_ascii=False,
                )
            )
        return Completion(
            text=(
                "围绕该议题，本资源给出结构化讲解正文：包含概念定义、关键直觉、典型示例与要点总结，"
                "内容足够长以稳定通过基于长度（>50 字）的质量校验规则，并可作为下游辩论与组装阶段的上下文。"
            )
        )


@pytest.mark.asyncio
async def test_debate_end_to_end_reachable():
    """astream 从 START：goal 含辩论关键词 → planner 点火 conflict → 真正走到 debate→judge，
    短路 critic，辩论结论作为 type=debate 资源进入 bundle。验证集成层点火打通。"""
    from reflexlearn.orchestration.graph import build_graph

    graph = build_graph(_E2EDebateLLM())
    initial = {
        "user_id": "u1", "acl": {"user_id": "u1"},
        "messages": [{"role": "user", "content": "辩论"}],
        "learner_profile": {}, "learning_goal": "该不该用深度学习做小样本分类（利弊辨析）",
        "collab_mode": "central",
        "plan": [], "completed": [], "reflections": [],
        "iteration": 0, "replan_count": 0, "token_used": 0,
        "halt_reason": None, "conflict": None,
        "debate_rounds": None, "debate_verdict": None,
        "resource_bundle": None, "learning_path": None,
    }

    seen, final = [], None
    async for event in graph.astream(initial, stream_mode="updates"):
        for node_name, output in event.items():
            seen.append(node_name)
            if node_name == "assemble":
                final = output

    assert "debate" in seen          # 真正进入辩论节点
    assert "judge" in seen           # 裁决节点
    assert "critic" not in seen      # conflict 优先，短路 critic
    resources = final["resource_bundle"]["resources"]
    assert any(r.get("type") == "debate" and r.get("task_id") == "debate-verdict" for r in resources)
    assert final["resource_bundle"]["total"] >= 6   # 5 资源 + 辩论结论
