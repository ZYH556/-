from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.orchestration.nodes.reflection.metacognition import metacognition_node


class _FakeLLM:
    def __init__(self, payload: dict | None = None, should_fail: bool = False):
        self.payload = payload or {}
        self.should_fail = should_fail
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        if self.should_fail:
            raise RuntimeError("llm_no_api_key")
        return Completion(text=json.dumps(self.payload, ensure_ascii=False))


def _state(llm) -> dict:
    return {
        "_llm": llm,
        "learning_goal": "学习线性回归",
        "learner_profile": {},
        "completed": [
            {
                "task_id": "t1",
                "type": "doc",
                "status": "passed",
                "content": "一份质量一般的学习资源",
            }
        ],
        "plan": [
            {
                "task_id": "t1",
                "type": "doc",
                "status": "pending",
                "spec": {"concept_ids": ["linear_regression"], "difficulty": 0.4},
                "attempts": 0,
                "result_ref": None,
            }
        ],
        "self_refine_count": 0,
    }


@pytest.mark.asyncio
async def test_metacognition_low_score_marks_task_for_refine(monkeypatch):
    monkeypatch.setenv("ENABLE_METACOGNITION", "true")
    from reflexlearn.common.config import get_settings

    get_settings.cache_clear()
    llm = _FakeLLM(
        {
            "score": 0.42,
            "issues": ["示例不足"],
            "refine_hint": "补充一个梯度下降数值例子",
            "suggested_skill": "doc_gen",
        }
    )
    state = _state(llm)
    try:
        out = await metacognition_node(state)
    finally:
        get_settings.cache_clear()

    assert llm.calls[0]["kwargs"]["task_type"] == "reasoning"
    assert out["self_refine_count"] == 1
    assert out["plan"][0]["spec"]["refine_hint"] == "补充一个梯度下降数值例子"
    assert out["plan"][0]["spec"]["suggested_skill"] == "doc_gen"
    assert state["completed"][0]["status"] == "needs_refine"
    assert out["meta_reviews"][0]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_metacognition_llm_failure_degrades_to_noop(monkeypatch):
    monkeypatch.setenv("ENABLE_METACOGNITION", "true")
    from reflexlearn.common.config import get_settings

    get_settings.cache_clear()
    state = _state(_FakeLLM(should_fail=True))
    try:
        out = await metacognition_node(state)
    finally:
        get_settings.cache_clear()

    assert out["meta_reviews"][0]["status"] == "degraded"
    assert out["meta_reviews"][0]["reason"] == "RuntimeError"
    assert state["completed"][0]["status"] == "passed"


@pytest.mark.asyncio
async def test_metacognition_limits_reviews_and_compresses_payload(monkeypatch):
    monkeypatch.setenv("ENABLE_METACOGNITION", "true")
    monkeypatch.setenv("METACOGNITION_MAX_REVIEWS", "1")
    monkeypatch.setenv("METACOGNITION_CONTENT_CHARS", "40")
    from reflexlearn.common.config import get_settings

    get_settings.cache_clear()
    llm = _FakeLLM(
        {
            "score": 0.9,
            "issues": [],
            "refine_hint": "",
            "suggested_skill": "",
        }
    )
    state = _state(llm)
    state["completed"][0]["content"] = "x" * 200
    state["completed"].append(
        {"task_id": "t2", "type": "quiz", "status": "passed", "content": "y" * 200}
    )
    try:
        out = await metacognition_node(state)
    finally:
        get_settings.cache_clear()

    payload = json.loads(llm.calls[0]["messages"][1]["content"])
    assert len(llm.calls) == 1
    assert len(payload["summary"]) == 40
    assert out["meta_reviews"][0]["status"] == "ok"


def test_default_settings_keep_metacognition_disabled():
    from reflexlearn.common.config import Settings

    settings = Settings()

    assert settings.enable_metacognition is False
    assert settings.max_self_refine == 1
    assert settings.metacognition_max_reviews == 1
    assert settings.metacognition_timeout_s == 12.0
    assert settings.metacognition_min_score == 0.7
