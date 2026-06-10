from __future__ import annotations

import json

import pytest

from reflexlearn.llm_gateway.gateway import Completion
import reflexlearn.orchestration.nodes.reflection.critic as critic_module
from reflexlearn.orchestration.nodes.reflection.critic import critic_node
from reflexlearn.orchestration.schemas import Reflection


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
        "learner_profile": {"cognitive_style": "active"},
        "learning_goal": "学习线性回归",
        "plan": [],
        "completed": [
            {
                "task_id": "t1",
                "status": "failed",
                "type": "doc",
                "issues": ["内容过短"],
            }
        ],
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
async def test_critic_uses_llm_reflection(monkeypatch):
    persisted = []

    async def fake_persist(reflection, user_id):
        persisted.append((reflection, user_id))

    monkeypatch.setattr(critic_module, "_persist_reflection", fake_persist)
    llm = FakeLLM(
        {
            "task_type": "doc",
            "failure_type": "format",
            "cause": "内容过短",
            "fix_strategy": "补充例子和推导",
            "success": False,
        }
    )

    result = await critic_node(base_state(llm))

    assert result["replan_count"] == 1
    assert result["reflections"][0]["fix_strategy"] == "补充例子和推导"
    assert persisted[0][1] == "u1"
    assert llm.calls[0]["kwargs"]["task_type"] == "reasoning"


@pytest.mark.asyncio
async def test_critic_falls_back_without_crashing(monkeypatch):
    async def fake_persist(reflection, user_id):
        return None

    monkeypatch.setattr(critic_module, "_persist_reflection", fake_persist)

    result = await critic_node(base_state(FakeLLM(should_fail=True)))

    reflection = result["reflections"][0]
    assert result["replan_count"] == 1
    assert reflection["task_type"] == "doc"
    assert "内容过短" in reflection["failure_type"]


@pytest.mark.asyncio
async def test_persist_reflection_stamps_created_at(monkeypatch):
    captured = {}

    async def fake_pg_pool():
        return None

    def fake_qdrant():
        return object()

    async def fake_write(*, pg_pool, qdrant, reflection, user_id, created_at):
        captured.update(user_id=user_id, created_at=created_at, reflection=reflection)
        return True

    monkeypatch.setattr(critic_module, "get_pg_pool", fake_pg_pool)
    monkeypatch.setattr(critic_module, "get_qdrant", fake_qdrant)
    monkeypatch.setattr(critic_module, "write_reflection", fake_write)

    await critic_module._persist_reflection(
        Reflection(
            task_type="doc",
            failure_type="format",
            cause="内容过短",
            fix_strategy="补充例子",
            success=False,
        ),
        "u1",
    )

    assert captured["user_id"] == "u1"
    assert "T" in captured["created_at"]
    assert captured["reflection"].task_type == "doc"
