from __future__ import annotations

import json

import pytest

import reflexlearn.orchestration.graph as graph_mod
from reflexlearn.memory import session_store
from reflexlearn.orchestration.graph import run_session


class _FakeLLM:
    """planning 返回 1 个 doc 任务（central 模式）；其余返回足够长文本通过质检。"""

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        from reflexlearn.llm_gateway.gateway import Completion

        if task_type == "planning":
            return Completion(
                text=json.dumps(
                    {
                        "tasks": [
                            {
                                "type": "doc",
                                "concept_ids": ["c1"],
                                "difficulty": 0.4,
                                "style_hint": "active",
                                "constraints": [],
                            }
                        ]
                    },
                    ensure_ascii=False,
                )
            )
        return Completion(
            text="ML teaching content long enough to pass the length based quality rule check easily."
        )


class _MemStore:
    """内存 session 存储，替身 Redis 薄封装（load/persist 同名）。"""

    def __init__(self):
        self.data: dict[str, dict] = {}
        self.persist_calls = 0

    async def load(self, sid):
        d = self.data.get(sid)
        if not d:
            return {"messages": [], "summary_layers": []}
        return {
            "messages": list(d["messages"]),
            "summary_layers": list(d["summary_layers"]),
        }

    async def persist(self, sid, *, messages, summary_layers):
        self.persist_calls += 1
        self.data[sid] = {
            "messages": list(messages),
            "summary_layers": list(summary_layers),
        }
        return True


def _inject_fake_llm(monkeypatch):
    """patch build_graph，让 run_session 用可控 _FakeLLM（run_session 内部 build_graph() 无参）。"""
    real_build = graph_mod.build_graph
    monkeypatch.setattr(graph_mod, "build_graph", lambda *a, **k: real_build(_FakeLLM()))


async def _run_collect(message, user_id, session_id):
    seen = []
    async for event in run_session(message, user_id, session_id):
        seen.extend(event.keys())
    return seen


@pytest.mark.asyncio
async def test_multi_turn_accumulates_history(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    # 第一轮
    await _run_collect("线性回归", "u1", "sid-A")
    after_first = mem.data["sid-A"]["messages"]
    assert len(after_first) == 2  # user + assistant 轻量摘要
    assert after_first[0] == {"role": "user", "content": "线性回归"}
    assert after_first[1]["role"] == "assistant"

    # 第二轮（同 sid）：载入第一轮历史并累积
    await _run_collect("梯度下降", "u1", "sid-A")
    after_second = mem.data["sid-A"]["messages"]
    assert len(after_second) == 4  # 累积：u1 a1 u2 a2
    assert after_second[0]["content"] == "线性回归"  # 第一轮 user 仍在
    assert after_second[2]["content"] == "梯度下降"  # 第二轮 user
    assert mem.persist_calls == 2


@pytest.mark.asyncio
async def test_sessions_are_isolated(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    await _run_collect("线性回归", "u1", "sid-A")
    await _run_collect("神经网络", "u2", "sid-B")

    # 两个 session 各自独立，互不串台
    assert mem.data["sid-A"]["messages"][0]["content"] == "线性回归"
    assert mem.data["sid-B"]["messages"][0]["content"] == "神经网络"
    assert len(mem.data["sid-A"]["messages"]) == 2
    assert len(mem.data["sid-B"]["messages"]) == 2


@pytest.mark.asyncio
async def test_redis_down_degrades_to_single_turn(monkeypatch):
    """load 恒空 + persist 恒 False（模拟 Redis 挂）：run_session 仍端到端跑通、不抛错、不累积。"""
    _inject_fake_llm(monkeypatch)

    async def _load_empty(sid):
        return {"messages": [], "summary_layers": []}

    async def _persist_fail(sid, *, messages, summary_layers):
        return False

    monkeypatch.setattr(session_store, "load", _load_empty)
    monkeypatch.setattr(session_store, "persist", _persist_fail)

    seen1 = await _run_collect("线性回归", "u1", "sid-X")
    seen2 = await _run_collect("梯度下降", "u1", "sid-X")
    assert "assemble" in seen1  # 端到端跑通
    assert "assemble" in seen2


@pytest.mark.asyncio
async def test_no_session_id_is_single_turn(monkeypatch):
    """session_id 为空：完全不触碰 session_store，等价改造前单轮。"""
    _inject_fake_llm(monkeypatch)
    called = {"load": 0, "persist": 0}

    async def _load(sid):
        called["load"] += 1
        return {"messages": [], "summary_layers": []}

    async def _persist(sid, *, messages, summary_layers):
        called["persist"] += 1
        return True

    monkeypatch.setattr(session_store, "load", _load)
    monkeypatch.setattr(session_store, "persist", _persist)

    seen = await _run_collect("线性回归", "u1", "")
    assert "assemble" in seen
    assert called["load"] == 0
    assert called["persist"] == 0


@pytest.mark.asyncio
async def test_long_history_triggers_recursive_summary(monkeypatch):
    """预置超窗口历史：persist 时 overflow 触发递归摘要（无凭证 → 规则截断，layers 非空）。"""
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    # 14 条历史 > recent_turns(6)*2=12 → 本轮再 +2 = 16，溢出 4 条进摘要
    mem.data["sid-L"] = {
        "messages": [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"轮次{i}"}
            for i in range(14)
        ],
        "summary_layers": [],
    }
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    await _run_collect("新问题", "u1", "sid-L")
    assert len(mem.data["sid-L"]["summary_layers"]) >= 1  # 触发了摘要压缩
