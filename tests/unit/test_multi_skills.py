from __future__ import annotations

import pytest

from reflexlearn.orchestration.nodes.generator import generate_resource
from reflexlearn.skills.base import SkillResult


class FakeGenSkill:
    def __init__(self, label: str):
        self.label = label
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        return SkillResult(ok=True, data={"content": f"{self.label} 内容足够长，可以通过质量检查。"})


class PassQualitySkill:
    async def run(self, inp, ctx):
        return SkillResult(ok=True, data={"passed": True, "issues": [], "fixable": True})


def state_for(task_type: str, skills: dict) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {},
        "learning_goal": "学习线性回归",
        "plan": [
            {
                "task_id": "task-1",
                "type": task_type,
                "spec": {
                    "type": task_type,
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
        "_skills": skills,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_type", "skill_name"),
    [
        ("quiz", "quiz_gen"),
        ("mindmap", "mindmap_gen"),
        ("code", "code_gen"),
        ("reading", "reading_gen"),
    ],
)
async def test_generator_selects_type_specific_skill(task_type: str, skill_name: str):
    selected = FakeGenSkill(skill_name)
    doc = FakeGenSkill("doc_gen")
    skills = {
        "doc_gen": doc,
        skill_name: selected,
        "quality_check": PassQualitySkill(),
    }

    result = await generate_resource(state_for(task_type, skills))

    assert result["completed"][0]["status"] == "passed"
    assert result["completed"][0]["type"] == task_type
    assert len(selected.calls) == 1
    assert len(doc.calls) == 0
