from __future__ import annotations

import pytest

import reflexlearn.orchestration.graph as graph_mod
from reflexlearn.common.config import get_settings
from reflexlearn.memory import session_store
from reflexlearn.memory.graph_autogrow import autogrow_session_graph


class _FakeGraph:
    async def astream(self, state, stream_mode):
        yield {"assemble": {"resource_bundle": {"total": 1}, "learner_profile": {"goal": "g"}}}


@pytest.mark.asyncio
async def test_run_session_triggers_graph_autogrow_after_persist(monkeypatch):
    captured = []

    async def fake_autogrow(**kwargs):
        captured.append(kwargs)
        return "ok", 1, 0, []

    async def load(_sid):
        return {"messages": [], "summary_layers": []}

    async def persist(_sid, *, messages, summary_layers):
        return True

    async def load_profile(_user_id, *, tenant_id):
        return {}

    async def save_profile(_user_id, *, tenant_id, profile):
        return True

    monkeypatch.setenv("ENABLE_GRAPH_AUTOGROW", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(graph_mod, "build_graph", lambda _llm: _FakeGraph())
    monkeypatch.setattr(graph_mod, "autogrow_session_graph", fake_autogrow, raising=False)
    monkeypatch.setattr(session_store, "load", load)
    monkeypatch.setattr(session_store, "persist", persist)
    monkeypatch.setattr(session_store, "load_profile", load_profile)
    monkeypatch.setattr(session_store, "save_profile", save_profile)
    try:
        async for _ in graph_mod.run_session("线性回归", "u1", "sid", "tenant-a"):
            pass
    finally:
        get_settings.cache_clear()

    assert captured
    assert captured[0]["tenant_id"] == "tenant-a"
    assert captured[0]["visibility"] == "public"
    assert "线性回归" in captured[0]["text"]
    assert "[已生成 1 个学习资源]" in captured[0]["text"]


@pytest.mark.asyncio
async def test_autogrow_session_graph_skips_when_disabled(monkeypatch):
    class _Settings:
        enable_graph_autogrow = False
        graph_extract_max_chars = 8000

    called = {"n": 0}

    async def fake_build_graph(**kwargs):
        called["n"] += 1
        return "ok", 1, 0, []

    monkeypatch.setattr(
        "reflexlearn.memory.graph_autogrow.graph_build.build_graph",
        fake_build_graph,
    )

    status, concepts, relations, notes = await autogrow_session_graph(
        text="线性回归\n[已生成 1 个学习资源]",
        tenant_id="tenant-a",
        visibility="public",
        doc_id="session:u1:sid",
        neo4j=object(),
        settings=_Settings(),
        gateway=object(),
    )

    assert (status, concepts, relations) == ("disabled", 0, 0)
    assert notes == []
    assert called["n"] == 0
