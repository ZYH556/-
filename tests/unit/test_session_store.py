from __future__ import annotations

import json

import pytest

from reflexlearn.common.config import get_settings
from reflexlearn.memory import session_store


class _FakeRedis:
    """内存 mock，可注入 fail 触发连接异常，验证降级。"""

    def __init__(self, fail: bool = False):
        self.store: dict[str, str] = {}
        self.fail = fail
        self.set_calls: list[dict] = []

    async def get(self, key):
        if self.fail:
            raise RuntimeError("redis down")
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        if self.fail:
            raise RuntimeError("redis down")
        self.store[key] = value
        self.set_calls.append({"key": key, "value": value, "ex": ex})


def _patch(monkeypatch, fake: _FakeRedis):
    async def _get_redis():
        return fake

    monkeypatch.setattr(session_store, "get_redis", _get_redis)


@pytest.mark.asyncio
async def test_persist_then_load_roundtrip(monkeypatch):
    fake = _FakeRedis()
    _patch(monkeypatch, fake)

    ok = await session_store.persist(
        "sid1",
        messages=[{"role": "user", "content": "线性回归"}],
        summary_layers=["第一层摘要"],
    )
    assert ok is True

    data = await session_store.load("sid1")
    assert data["messages"] == [{"role": "user", "content": "线性回归"}]
    assert data["summary_layers"] == ["第一层摘要"]


@pytest.mark.asyncio
async def test_load_missing_key_returns_empty(monkeypatch):
    _patch(monkeypatch, _FakeRedis())
    assert await session_store.load("nope") == {"messages": [], "summary_layers": []}


@pytest.mark.asyncio
async def test_load_redis_down_degrades_to_empty(monkeypatch):
    _patch(monkeypatch, _FakeRedis(fail=True))
    assert await session_store.load("sid") == {"messages": [], "summary_layers": []}


@pytest.mark.asyncio
async def test_persist_redis_down_returns_false(monkeypatch):
    _patch(monkeypatch, _FakeRedis(fail=True))
    ok = await session_store.persist(
        "sid", messages=[{"role": "user", "content": "x"}], summary_layers=[]
    )
    assert ok is False


@pytest.mark.asyncio
async def test_load_corrupt_json_returns_empty(monkeypatch):
    fake = _FakeRedis()
    fake.store["session:sid"] = "{not valid json"
    _patch(monkeypatch, fake)
    assert await session_store.load("sid") == {"messages": [], "summary_layers": []}


@pytest.mark.asyncio
async def test_empty_session_id_never_touches_redis(monkeypatch):
    called = {"n": 0}

    async def _get_redis():
        called["n"] += 1
        return _FakeRedis()

    monkeypatch.setattr(session_store, "get_redis", _get_redis)
    assert await session_store.load("") == {"messages": [], "summary_layers": []}
    assert await session_store.persist("", messages=[], summary_layers=[]) is False
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_persist_sets_ttl_and_truncates_messages(monkeypatch):
    fake = _FakeRedis()
    _patch(monkeypatch, fake)

    msgs = [{"role": "user", "content": str(i)} for i in range(50)]
    await session_store.persist("sid", messages=msgs, summary_layers=[])

    assert fake.set_calls[0]["ex"] == get_settings().session_ttl
    stored = json.loads(fake.store["session:sid"])
    assert len(stored["messages"]) == session_store.MAX_PERSISTED_MESSAGES
    # 截断保留的是最近 N 条
    assert stored["messages"][-1] == {"role": "user", "content": "49"}


def test_scoped_session_id_is_bound_to_user_and_tenant():
    base = session_store.scoped_session_id("sid", user_id="u1", tenant_id="t1")

    assert base
    assert base == session_store.scoped_session_id("sid", user_id="u1", tenant_id="t1")
    assert base != session_store.scoped_session_id("sid", user_id="u2", tenant_id="t1")
    assert base != session_store.scoped_session_id("sid", user_id="u1", tenant_id="t2")
    assert session_store.scoped_session_id("", user_id="u1", tenant_id="t1") == ""
