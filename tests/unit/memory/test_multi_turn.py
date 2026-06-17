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

        if task_type == "profiling":
            payload = json.loads(messages[-1]["content"])
            existing = payload.get("existing_profile") or {}
            weak_points = list(existing.get("weak_points", []))
            if "跨会话薄弱点" not in weak_points:
                weak_points.append("跨会话薄弱点")
            return Completion(
                text=json.dumps(
                    {
                        "knowledge_base": {"python": 0.8},
                        "cognitive_style": existing.get("cognitive_style", "active"),
                        "goal": payload.get("learning_goal", ""),
                        "weak_points": weak_points,
                        "preferences": existing.get("preferences", {}),
                        "progress": max(float(existing.get("progress", 0.0)), 0.2),
                    },
                    ensure_ascii=False,
                )
            )
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


class _ProfileStore:
    def __init__(self):
        self.data: dict[tuple[str, str], dict] = {}
        self.load_calls: list[tuple[str, str]] = []
        self.save_calls: list[tuple[str, str, dict]] = []

    async def load_profile(self, user_id, *, tenant_id):
        self.load_calls.append((tenant_id, user_id))
        return dict(self.data.get((tenant_id, user_id), {}))

    async def save_profile(self, user_id, *, tenant_id, profile):
        self.save_calls.append((tenant_id, user_id, dict(profile)))
        self.data[(tenant_id, user_id)] = dict(profile)
        return True


def _inject_fake_llm(monkeypatch):
    """patch build_graph，让 run_session 用可控 _FakeLLM（run_session 内部 build_graph() 无参）。"""
    real_build = graph_mod.build_graph
    monkeypatch.setattr(graph_mod, "build_graph", lambda *a, **k: real_build(_FakeLLM()))


def _scoped(sid: str, user_id: str, tenant_id: str = "default") -> str:
    return session_store.scoped_session_id(sid, user_id=user_id, tenant_id=tenant_id)


async def _run_collect(message, user_id, session_id, tenant_id="default"):
    seen = []
    async for event in run_session(message, user_id, session_id, tenant_id):
        seen.extend(event.keys())
    # PERF-C：PERSIST 后台化，断言持久化副作用前先收尾后台 task
    from reflexlearn.orchestration.graph import drain_persist_tasks

    await drain_persist_tasks()
    return seen


@pytest.mark.asyncio
async def test_multi_turn_accumulates_history(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    # 第一轮
    await _run_collect("线性回归", "u1", "sid-A")
    scoped = _scoped("sid-A", "u1")
    after_first = mem.data[scoped]["messages"]
    assert len(after_first) == 2  # user + assistant 轻量摘要
    assert after_first[0] == {"role": "user", "content": "线性回归"}
    assert after_first[1]["role"] == "assistant"

    # 第二轮（同 sid）：载入第一轮历史并累积
    await _run_collect("梯度下降", "u1", "sid-A")
    after_second = mem.data[scoped]["messages"]
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
    sid_a = _scoped("sid-A", "u1")
    sid_b = _scoped("sid-B", "u2")
    assert mem.data[sid_a]["messages"][0]["content"] == "线性回归"
    assert mem.data[sid_b]["messages"][0]["content"] == "神经网络"
    assert len(mem.data[sid_a]["messages"]) == 2
    assert len(mem.data[sid_b]["messages"]) == 2


@pytest.mark.asyncio
async def test_same_session_id_is_isolated_between_users(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    await _run_collect("线性回归", "u1", "shared-sid")
    await _run_collect("神经网络", "u2", "shared-sid")

    histories = [item["messages"] for item in mem.data.values()]
    assert len(histories) == 2
    assert sorted(history[0]["content"] for history in histories) == ["神经网络", "线性回归"]
    assert all(len(history) == 2 for history in histories)


@pytest.mark.asyncio
async def test_same_session_id_is_isolated_between_tenants(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    await _run_collect("租户一问题", "u1", "shared-sid", tenant_id="tenant-a")
    await _run_collect("租户二问题", "u1", "shared-sid", tenant_id="tenant-b")

    histories = [item["messages"] for item in mem.data.values()]
    assert len(histories) == 2
    assert sorted(history[0]["content"] for history in histories) == ["租户一问题", "租户二问题"]
    assert all(len(history) == 2 for history in histories)


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
    scoped = _scoped("sid-L", "u1")
    # 14 条历史 > recent_turns(6)*2=12 → 本轮再 +2 = 16，溢出 4 条进摘要
    mem.data[scoped] = {
        "messages": [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"轮次{i}"}
            for i in range(14)
        ],
        "summary_layers": [],
    }
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)

    await _run_collect("新问题", "u1", "sid-L")
    assert len(mem.data[scoped]["summary_layers"]) >= 1  # 触发了摘要压缩


@pytest.mark.asyncio
async def test_cross_session_profile_is_loaded_and_saved(monkeypatch):
    _inject_fake_llm(monkeypatch)
    mem = _MemStore()
    profiles = _ProfileStore()
    profiles.data[("default", "u1")] = {
        "knowledge_base": {"statistics": 0.2},
        "cognitive_style": "reflective",
        "goal": "历史目标",
        "weak_points": ["历史薄弱点"],
        "preferences": {"prefer_code_examples": True},
        "progress": 0.1,
    }
    monkeypatch.setattr(session_store, "load", mem.load)
    monkeypatch.setattr(session_store, "persist", mem.persist)
    monkeypatch.setattr(session_store, "load_profile", profiles.load_profile)
    monkeypatch.setattr(session_store, "save_profile", profiles.save_profile)

    await _run_collect("新的学习目标", "u1", "sid-profile")

    assert profiles.load_calls == [("default", "u1")]
    assert profiles.save_calls
    saved = profiles.save_calls[-1][2]
    assert saved["cognitive_style"] == "reflective"
    assert "历史薄弱点" in saved["weak_points"]
    assert "跨会话薄弱点" in saved["weak_points"]
    assert saved["progress"] == 0.2


@pytest.mark.asyncio
async def test_persist_runs_in_background(monkeypatch):
    """PERF-C：PERSIST 后台化——run_session 消费结束时持久化尚未完成（done 帧不等它）。"""
    import asyncio

    _inject_fake_llm(monkeypatch)
    gate = asyncio.Event()
    done = {"persisted": False}

    async def slow_load(sid):
        return {"messages": [], "summary_layers": []}

    async def slow_persist(sid, *, messages, summary_layers):
        await gate.wait()  # 卡住直到测试放行
        done["persisted"] = True
        return True

    monkeypatch.setattr(session_store, "load", slow_load)
    monkeypatch.setattr(session_store, "persist", slow_persist)

    async for _ in run_session("线性回归", "u1", "sid-bg"):
        pass
    # 消费完所有图事件（含 done 等价）后，persist 仍卡在 gate 上 → 证明它在后台、未阻塞主流
    assert done["persisted"] is False

    gate.set()
    await graph_mod.drain_persist_tasks()
    assert done["persisted"] is True
