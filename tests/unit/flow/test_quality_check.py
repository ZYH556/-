from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.quality_check import QualityCheckSkill


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


@pytest.mark.asyncio
async def test_quality_check_uses_llm_judge():
    skill = QualityCheckSkill(
        FakeLLM(
            {
                "passed": True,
                "layer_failed": "none",
                "score": 0.92,
                "issues": [],
                "fixable": True,
            }
        )
    )

    result = await skill.run(
        {"content": "一份完整的学习资源", "spec": {}, "profile": {}},
        SkillContext(user_id="u1", acl={}, task_id="t1"),
    )

    assert result.data["passed"] is True
    assert result.data["score"] == 0.92
    assert skill.llm.calls[0]["kwargs"]["task_type"] == "verification"
    assert skill.llm.calls[0]["kwargs"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_quality_check_falls_back_to_rules():
    skill = QualityCheckSkill(FakeLLM(should_fail=True))

    result = await skill.run(
        {"content": "短"},
        SkillContext(user_id="u1", acl={}, task_id="t1"),
    )

    assert result.data["passed"] is False
    assert result.data["layer_failed"] == "format"
    assert result.data["issues"] == ["内容过短"]
