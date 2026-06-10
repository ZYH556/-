from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.nodes.core.profile import profile_node


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


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def base_state(llm) -> dict:
    return {
        "learning_goal": "学习线性回归",
        "messages": [{"role": "user", "content": "我想用代码学习线性回归"}],
        "learner_profile": {},
        "iteration": 0,
        "_llm": llm,
    }


@pytest.mark.asyncio
async def test_profile_uses_llm_json_schema():
    llm = FakeLLM(
        {
            "knowledge_base": {"python": 0.8, "statistics": 0.3},
            "cognitive_style": "active",
            "goal": "学习线性回归",
            "weak_points": ["统计推导"],
            "preferences": {"prefer_code_examples": True},
            "progress": 0.1,
        }
    )

    result = await profile_node(base_state(llm))

    assert result["learner_profile"]["cognitive_style"] == "active"
    assert result["learner_profile"]["weak_points"] == ["统计推导"]
    assert llm.calls[0]["kwargs"]["task_type"] == "profiling"
    assert llm.calls[0]["kwargs"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_profile_falls_back_when_llm_fails():
    result = await profile_node(base_state(FakeLLM(should_fail=True)))

    assert result["learner_profile"]["goal"] == "学习线性回归"
    assert "数学推导" in result["learner_profile"]["weak_points"]


@pytest.mark.asyncio
async def test_profile_skips_llm_when_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_PROFILE", "false")

    from reflexlearn.common.config import get_settings

    get_settings.cache_clear()
    llm = FakeLLM()
    try:
        result = await profile_node(base_state(llm))
    finally:
        get_settings.cache_clear()

    assert llm.calls == []
    assert result["learner_profile"]["goal"] == "学习线性回归"
