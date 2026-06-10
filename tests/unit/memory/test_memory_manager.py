from __future__ import annotations

import pytest

import reflexlearn.memory.manager as mgr
from reflexlearn.memory.manager import MemoryManager, recall_memory_node
from reflexlearn.orchestration.schemas import Reflection


def _reflection() -> Reflection:
    return Reflection(
        task_type="quiz",
        failure_type="format_error",
        cause="c",
        fix_strategy="fix",
        success=False,
    )


class _FakeLLM:
    async def complete(self, messages, **kw):
        from reflexlearn.llm_gateway.gateway import Completion

        return Completion(text="摘要X")


# —— L1 上下文工程：无状态转发 ——

def test_trim_context_forwards():
    m = MemoryManager()
    out = m.trim_context([{"role": "user", "content": "a"}], "", None)
    assert out == [{"role": "user", "content": "a"}]


def test_get_summary_context_forwards():
    m = MemoryManager()
    assert m.get_summary_context(["x", "y"]) == "x\n---\ny"
    assert m.get_summary_context([]) == ""


@pytest.mark.asyncio
async def test_update_summary_forwards():
    m = MemoryManager()
    layers = await m.update_summary([], [{"role": "user", "content": "内容"}], _FakeLLM())
    assert layers == ["摘要X"]


@pytest.mark.asyncio
async def test_update_summary_swallows_errors_keeps_old(monkeypatch):
    m = MemoryManager()

    async def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(mgr.recursive_summary, "add_and_compress", _boom)
    layers = await m.update_summary(["keep"], [{"role": "user", "content": "x"}], _FakeLLM())
    assert layers == ["keep"]  # 摘要失败兜底：保留旧 layers，不破坏多轮


# —— L1→L2 promote ——

@pytest.mark.asyncio
async def test_promote_forwards_to_write_reflection(monkeypatch):
    captured = {}

    async def _fake_write(*, pg_pool, qdrant, reflection, user_id, created_at):
        captured.update(
            pg_pool=pg_pool,
            qdrant=qdrant,
            reflection=reflection,
            user_id=user_id,
            created_at=created_at,
        )
        return True

    monkeypatch.setattr(mgr, "write_reflection", _fake_write)

    fake_q, fake_pg = object(), object()
    m = MemoryManager(qdrant=fake_q, pg_pool=fake_pg)
    ok = await m.promote_session(reflection=_reflection(), user_id="u1")

    assert ok is True
    assert captured["qdrant"] is fake_q
    assert captured["pg_pool"] is fake_pg
    assert captured["user_id"] == "u1"
    assert "T" in captured["created_at"]
    assert captured["reflection"].task_type == "quiz"


@pytest.mark.asyncio
async def test_promote_degrades_when_all_none():
    # 不传 qdrant/pg；conftest 拦 get_qdrant → None；write_reflection 无处可写 → False，不抛错
    m = MemoryManager()
    ok = await m.promote_session(reflection=_reflection(), user_id="u1")
    assert ok is False


# —— recall 回归（行为不变）——

@pytest.mark.asyncio
async def test_recall_empty_when_qdrant_blocked():
    m = MemoryManager()
    out = await m.recall(task_type="", query="线性回归", acl={"user_id": "u1"})
    assert out == []


@pytest.mark.asyncio
async def test_recall_memory_node_shape_unchanged():
    state = {"learning_goal": "g", "acl": {"user_id": "u1"}, "iteration": 2}
    out = await recall_memory_node(state)
    assert out["iteration"] == 3
    assert out["reflections"] == []


@pytest.mark.asyncio
async def test_recall_memory_node_skips_recall_when_reflexion_disabled(monkeypatch):
    from reflexlearn.common.config import get_settings

    class BoomManager:
        async def recall(self, *args, **kwargs):
            raise AssertionError("recall should be skipped")

    monkeypatch.setenv("ENABLE_REFLEXION", "false")
    get_settings.cache_clear()
    try:
        out = await recall_memory_node(
            {
                "_memory_manager": BoomManager(),
                "learning_goal": "g",
                "acl": {"user_id": "u1"},
                "iteration": 4,
            }
        )
    finally:
        get_settings.cache_clear()

    assert out == {"reflections": [], "iteration": 5}
