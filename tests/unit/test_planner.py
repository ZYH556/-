from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.nodes.planner import planner_node


class FakeLLM:
    def __init__(self, payload: dict | None = None, should_fail: bool = False):
        self.payload = payload or {}
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self.should_fail:
            raise RuntimeError("llm unavailable")
        return Completion(text=json.dumps(self.payload, ensure_ascii=False))


def base_state(llm) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {
            "knowledge_base": {"statistics": 0.4, "python": 0.7},
            "cognitive_style": "active",
            "weak_points": ["数学推导"],
        },
        "learning_goal": "学习线性回归的原理",
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
        "_llm": llm,
    }


@pytest.mark.asyncio
async def test_planner_uses_llm_json_plan():
    llm = FakeLLM(
        {
            "tasks": [
                {
                    "type": "doc",
                    "concept_ids": ["linear_regression"],
                    "difficulty": 0.45,
                    "style_hint": "active",
                    "constraints": ["包含直观例子"],
                },
                {
                    "type": "quiz",
                    "concept_ids": ["least_squares"],
                    "difficulty": 0.55,
                    "style_hint": "active",
                    "constraints": ["包含答案解析"],
                },
            ]
        }
    )

    result = await planner_node(base_state(llm))

    assert len(result["plan"]) == 2
    assert result["plan"][0]["type"] == "doc"
    assert result["plan"][1]["spec"]["type"] == "quiz"
    assert llm.calls[0]["kwargs"]["task_type"] == "planning"
    assert llm.calls[0]["kwargs"]["temperature"] == 0.1


@pytest.mark.asyncio
async def test_planner_falls_back_when_llm_fails():
    result = await planner_node(base_state(FakeLLM(should_fail=True)))

    plan = result["plan"]
    # 离线 / LLM 失败时降级为全部 6 种资源（doc 打头，附导图 / 练习 / 代码 / 拓展阅读 / 视频脚本），
    # 满足「≥5 种资源」P0 硬指标，并覆盖「多模态视频 / 动画」资源类型
    assert len(plan) == 6
    assert plan[0]["type"] == "doc"
    assert {p["type"] for p in plan} == {"doc", "mindmap", "quiz", "code", "reading", "video"}
    assert plan[0]["spec"]["concept_ids"] == ["学习线性回归的原理"]


@pytest.mark.asyncio
async def test_planner_fires_debate_on_keyword_offline():
    state = base_state(FakeLLM(should_fail=True))
    state["learning_goal"] = "该不该用深度学习做小样本分类？请辨析利弊"
    result = await planner_node(state)

    assert result["collab_mode"] == "debate"
    conflict = result["conflict"]
    assert conflict["has_conflict"] is True
    assert len(conflict["chunks"]) == 2
    # chunks 围绕 goal 生成（含目标文本），而非写死占位
    assert all(state["learning_goal"] in c["content"] for c in conflict["chunks"])
    assert conflict["chunks"][0]["source"].startswith("正方")
    assert conflict["chunks"][1]["source"].startswith("反方")
    # 辩论模式仍保留全部 6 种资源（fan_out 生成）
    assert len(result["plan"]) == 6


@pytest.mark.asyncio
async def test_planner_plain_goal_injects_no_conflict():
    # 默认 goal「学习线性回归的原理」不含辩论 / 流水线关键词 → central，不写 conflict key
    result = await planner_node(base_state(FakeLLM(should_fail=True)))
    assert result["collab_mode"] == "central"
    assert "conflict" not in result


@pytest.mark.asyncio
async def test_planner_respects_llm_debate_mode():
    llm = FakeLLM(
        {
            "tasks": [
                {"type": "doc", "concept_ids": ["c1"], "difficulty": 0.4, "style_hint": "active", "constraints": []},
            ],
            "collab_mode": "debate",
        }
    )
    result = await planner_node(base_state(llm))

    assert result["collab_mode"] == "debate"
    assert result["conflict"]["has_conflict"] is True


@pytest.mark.asyncio
async def test_planner_injects_summary_into_system_prompt():
    llm = FakeLLM(
        {"tasks": [{"type": "doc", "concept_ids": ["c1"], "difficulty": 0.4, "style_hint": "active", "constraints": []}]}
    )
    state = base_state(llm)
    state["summary_layers"] = ["用户已学完线性回归基础"]
    await planner_node(state)

    system_msg = llm.calls[0]["messages"][0]["content"]
    assert "历史对话摘要" in system_msg
    assert "用户已学完线性回归基础" in system_msg


@pytest.mark.asyncio
async def test_planner_no_summary_keeps_prompt_clean():
    llm = FakeLLM(
        {"tasks": [{"type": "doc", "concept_ids": ["c1"], "difficulty": 0.4, "style_hint": "active", "constraints": []}]}
    )
    # base_state 无 summary_layers → system prompt 不含摘要段（零回归）
    await planner_node(base_state(llm))
    system_msg = llm.calls[0]["messages"][0]["content"]
    assert "历史对话摘要" not in system_msg
