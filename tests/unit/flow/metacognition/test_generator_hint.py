from __future__ import annotations

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.nodes.core.generator import generate_resource
from reflexlearn.skills.base import SkillResult
from reflexlearn.skills.doc_gen import DocGenSkill


class _CaptureSkill:
    name = "doc_gen"
    max_calls_per_task = 3
    cache_ttl = None

    def __init__(self):
        self.specs: list[dict] = []

    async def run(self, inp, ctx):
        self.specs.append(inp["spec"])
        return SkillResult(ok=True, data={"content": "x" * 80})


@pytest.mark.asyncio
async def test_generator_injects_refine_hint_into_previous_issues():
    skill = _CaptureSkill()

    await generate_resource(
        {
            "user_id": "u1",
            "acl": {},
            "_skills": {"doc_gen": skill, "quality_check": None},
            "_current_task": {
                "task_id": "t1",
                "type": "doc",
                "status": "pending",
                "spec": {"concept_ids": ["c1"], "refine_hint": "补充例子"},
            },
        }
    )

    assert "补充例子" in skill.specs[0]["previous_issues"]


@pytest.mark.asyncio
async def test_doc_generator_includes_previous_issues_in_prompt():
    llm = _PromptCaptureLLM()
    skill = DocGenSkill(llm)

    await skill.run(
        {
            "spec": {
                "concept_ids": ["linear_regression"],
                "difficulty": 0.4,
                "previous_issues": ["补充梯度下降数值例子"],
            },
            "context": "",
        },
        ctx=_Ctx(),
    )

    assert "补充梯度下降数值例子" in llm.calls[0]["messages"][1]["content"]


class _PromptCaptureLLM:
    def __init__(self):
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return Completion(text="x" * 80)


class _Ctx:
    user_id = "u1"
    acl = {}
    task_id = "t1"
    trace_id = ""
