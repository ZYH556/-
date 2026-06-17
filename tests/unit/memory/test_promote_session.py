from __future__ import annotations

import json

import pytest

import reflexlearn.orchestration.graph as graph_mod
import reflexlearn.orchestration.persist as persist_mod
from reflexlearn.memory import session_store
from reflexlearn.orchestration.graph import run_session


class _FakeLLM:
    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        from reflexlearn.llm_gateway.gateway import Completion

        if task_type == "profiling":
            return Completion(
                text=json.dumps(
                    {
                        "knowledge_base": {"python": 0.7},
                        "cognitive_style": "active",
                        "goal": "g",
                        "weak_points": [],
                        "preferences": {},
                        "progress": 0.1,
                    }
                )
            )
        if task_type == "planning":
            return Completion(
                text=json.dumps(
                    {
                        "tasks": [
                            {
                                "type": "doc",
                                "concept_ids": ["linear_regression"],
                                "difficulty": 0.4,
                                "style_hint": "active",
                                "constraints": [],
                            }
                        ]
                    }
                )
            )
        return Completion(
            text="Long enough generated learning content for quality check and resource assembly."
        )


class _FakeMemoryManager:
    calls: list[dict] = []

    async def recall(self, task_type: str, query: str, acl: dict) -> list[dict]:
        return []

    async def promote_session(self, *, reflection, user_id: str) -> bool:
        self.__class__.calls.append({"reflection": reflection, "user_id": user_id})
        return True


def _inject_graph(monkeypatch):
    real_build = graph_mod.build_graph
    monkeypatch.setattr(graph_mod, "build_graph", lambda *a, **k: real_build(_FakeLLM()))


@pytest.mark.asyncio
async def test_run_session_promotes_success_reflection_when_enabled(monkeypatch):
    from reflexlearn.common.config import get_settings

    _FakeMemoryManager.calls = []
    _inject_graph(monkeypatch)
    monkeypatch.setenv("ENABLE_PROMOTE", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(persist_mod, "MemoryManager", _FakeMemoryManager)

    async def _load_profile(user_id, *, tenant_id):
        return {}

    async def _save_profile(user_id, *, tenant_id, profile):
        return True

    monkeypatch.setattr(session_store, "load_profile", _load_profile)
    monkeypatch.setattr(session_store, "save_profile", _save_profile)
    async def _load(sid):
        return {"messages": [], "summary_layers": []}

    async def _persist(sid, *, messages, summary_layers):
        return True

    monkeypatch.setattr(session_store, "load", _load)
    monkeypatch.setattr(session_store, "persist", _persist)

    try:
        async for _ in run_session("学习线性回归", "u1", "sid-promote"):
            pass
        from reflexlearn.orchestration.graph import drain_persist_tasks

        await drain_persist_tasks()  # PERF-C：PERSIST 后台化，断言前收尾
    finally:
        get_settings.cache_clear()

    assert _FakeMemoryManager.calls
    call = _FakeMemoryManager.calls[-1]
    assert call["user_id"] == "u1"
    assert call["reflection"].task_type == "session"
    assert call["reflection"].success is True
    assert "学习线性回归" in call["reflection"].cause
