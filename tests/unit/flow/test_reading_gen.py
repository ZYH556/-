from __future__ import annotations

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.reading_gen import ReadingGenSkill


class FakeLLM:
    def __init__(self):
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append(kwargs)
        return Completion(text="1. 《机器学习》周志华 第3章 —— 入门必读\n2. CS229 讲义 —— 进阶")


@pytest.mark.asyncio
async def test_reading_gen_produces_recommendations():
    llm = FakeLLM()
    skill = ReadingGenSkill(llm)

    result = await skill.run(
        {
            "spec": {"concept_ids": ["linear_regression"], "difficulty": 0.5, "style_hint": "active"},
            "context": "上游讲解文档内容",
        },
        SkillContext(user_id="u1", acl={}, task_id="t1"),
    )

    assert result.ok
    assert "第3章" in result.data["content"]
    assert llm.calls[0]["task_type"] == "generation"


@pytest.mark.asyncio
async def test_reading_gen_handles_llm_error():
    """LLM 任意运行时错误（宕机/凭证失效等）与无 key 行为一致：降级离线占位。"""

    class FailLLM:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("llm down")

    skill = ReadingGenSkill(FailLLM())
    result = await skill.run(
        {"spec": {"concept_ids": ["x"]}, "context": ""},
        SkillContext(user_id="u1", acl={}, task_id="t1"),
    )

    assert result.ok
    assert result.data["model_used"] == "offline"
    assert result.data["degraded_from"] == "RuntimeError"
    assert len(result.data["content"]) > 50
