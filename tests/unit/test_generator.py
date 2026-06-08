from __future__ import annotations

import pytest

from reflexlearn.orchestration.nodes.generator import generate_resource
from reflexlearn.skills.base import SkillResult


class FakeRetrieveSkill:
    async def run(self, inp, ctx):
        return SkillResult(ok=True, data={"chunks": [{"content": "线性回归上下文"}]})


class FakeGenSkill:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        index = min(len(self.calls) - 1, len(self.contents) - 1)
        return SkillResult(ok=True, data={"content": self.contents[index]})


class FakeQualitySkill:
    def __init__(self, checks: list[dict]):
        self.checks = checks
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        index = min(len(self.calls) - 1, len(self.checks) - 1)
        return SkillResult(ok=True, data=self.checks[index])


def base_state(gen_skill, quality_skill) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {"cognitive_style": "active"},
        "learning_goal": "学习线性回归",
        "plan": [
            {
                "task_id": "task-1",
                "type": "doc",
                "spec": {
                    "type": "doc",
                    "concept_ids": ["linear_regression"],
                    "difficulty": 0.5,
                    "style_hint": "active",
                    "constraints": [],
                },
                "status": "pending",
                "attempts": 0,
                "result_ref": None,
            }
        ],
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
        "_skills": {
            "retrieve": FakeRetrieveSkill(),
            "doc_gen": gen_skill,
            "quality_check": quality_skill,
        },
    }


@pytest.mark.asyncio
async def test_generator_retries_after_fixable_quality_failure():
    gen = FakeGenSkill(["短内容", "这是第二次生成的完整学习文档，包含概念解释、例子和总结。"])
    quality = FakeQualitySkill(
        [
            {"passed": False, "issues": ["内容过短"], "fixable": True},
            {"passed": True, "issues": [], "fixable": True},
        ]
    )

    result = await generate_resource(base_state(gen, quality))

    completed = result["completed"][0]
    assert completed["status"] == "passed"
    assert completed["react_steps"] == 2
    assert len(gen.calls) == 2
    assert gen.calls[1]["spec"]["previous_issues"] == ["内容过短"]


@pytest.mark.asyncio
async def test_generator_stops_on_unfixable_quality_failure():
    gen = FakeGenSkill(["错误内容"])
    quality = FakeQualitySkill(
        [{"passed": False, "issues": ["知识错误"], "fixable": False}]
    )

    result = await generate_resource(base_state(gen, quality))

    completed = result["completed"][0]
    assert completed["status"] == "failed"
    assert completed["issues"] == ["知识错误"]
    assert len(gen.calls) == 1
