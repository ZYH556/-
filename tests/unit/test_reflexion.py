"""Reflexion 经验记忆单测：真实向量写入 / 语义召回 / 降级 / ACL 兜底。

全程 mock embedding 与 qdrant，不加载真实模型、不连服务，验证封装逻辑与降级链。
"""
from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.memory.reflexion import recall_reflections, write_reflection
from reflexlearn.orchestration.schemas import Reflection


def _reflection() -> Reflection:
    return Reflection(
        task_type="quiz",
        failure_type="format_error",
        cause="题目 JSON 格式不符合 schema",
        fix_strategy="改用标准 JSON 模板并显式校验字段",
        success=False,
    )


def _boom_embed(*args, **kwargs):
    raise emb.EmbeddingUnavailable("model not loaded")


class _Point:
    def __init__(self, payload):
        self.payload = payload


class _QueryResponse:
    def __init__(self, points):
        self.points = points


class _FakeQdrant:
    def __init__(self, hits=None, scroll_points=None):
        self._hits = hits or []
        self._scroll_points = scroll_points or []
        self.queries: list[dict] = []
        self.scrolls: list[dict] = []
        self.upserts: list[dict] = []

    async def query_points(self, **kwargs):
        self.queries.append(kwargs)
        return _QueryResponse(self._hits)

    async def scroll(self, **kwargs):
        self.scrolls.append(kwargs)
        return self._scroll_points, None

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs)


class _FakePgConn:
    async def execute(self, *args, **kwargs):
        return "INSERT 0 1"


class _AcquireCtx:
    async def __aenter__(self):
        return _FakePgConn()

    async def __aexit__(self, *exc):
        return False


class _FakePgPool:
    def acquire(self):
        return _AcquireCtx()


# ---------------------------------------------------------------- 写入


@pytest.mark.asyncio
async def test_write_uses_real_vector(monkeypatch):
    """embedding 可用 → upsert 真实非零向量 + 完整 payload（杜绝 [0.0]*1024 占位）。"""
    monkeypatch.setattr(emb, "embed_documents", lambda texts: [[0.1] * emb.EMBED_DIM])
    fake = _FakeQdrant()

    ok = await write_reflection(pg_pool=None, qdrant=fake, reflection=_reflection(), user_id="u1")

    assert ok is True
    assert len(fake.upserts) == 1
    point = fake.upserts[0]["points"][0]
    assert len(point.vector) == emb.EMBED_DIM
    assert any(v != 0.0 for v in point.vector)  # 真实向量，非零占位
    assert point.payload["user_id"] == "u1"
    assert point.payload["task_type"] == "quiz"
    assert point.payload["failure_type"] == "format_error"


@pytest.mark.asyncio
async def test_write_embeds_semantic_fields(monkeypatch):
    """入库向量来自 reflection 的语义要素（task_type/cause/fix_strategy），保证可被语义召回。"""
    captured: dict = {}

    def fake_embed(texts):
        captured["texts"] = texts
        return [[0.2] * emb.EMBED_DIM]

    monkeypatch.setattr(emb, "embed_documents", fake_embed)
    await write_reflection(pg_pool=None, qdrant=_FakeQdrant(), reflection=_reflection(), user_id="u1")

    text = captured["texts"][0]
    assert "quiz" in text
    assert "题目 JSON 格式不符合 schema" in text
    assert "改用标准 JSON 模板并显式校验字段" in text


@pytest.mark.asyncio
async def test_write_skips_qdrant_when_embedding_unavailable(monkeypatch):
    """embedding 不可用 → 跳过 qdrant 写入（绝不写零向量），返回 False。"""
    monkeypatch.setattr(emb, "embed_documents", _boom_embed)
    fake = _FakeQdrant()

    ok = await write_reflection(pg_pool=None, qdrant=fake, reflection=_reflection(), user_id="u1")

    assert ok is False
    assert fake.upserts == []  # 绝不写入零向量


@pytest.mark.asyncio
async def test_write_pg_persists_even_when_embedding_down(monkeypatch):
    """embedding 不可用时 qdrant 跳过，但 PG 仍持久化（纯增强：可降级不丢数据）。"""
    monkeypatch.setattr(emb, "embed_documents", _boom_embed)
    fake = _FakeQdrant()

    ok = await write_reflection(pg_pool=_FakePgPool(), qdrant=fake, reflection=_reflection(), user_id="u1")

    assert ok is True  # PG 写入成功
    assert fake.upserts == []  # qdrant 跳过，无零向量污染


# ---------------------------------------------------------------- 召回


@pytest.mark.asyncio
async def test_recall_semantic_uses_query_points(monkeypatch):
    """embedding 可用 → 走 query_points 语义检索（非 scroll），dict 结构正确且携带 query。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    hit = _Point(
        {
            "user_id": "u1",
            "task_type": "quiz",
            "failure_type": "format_error",
            "cause": "题目格式错误",
            "fix_strategy": "用标准模板",
            "success": False,
        }
    )
    fake = _FakeQdrant(hits=[hit])

    res = await recall_reflections(qdrant=fake, task_type="", query="线性回归测验", acl={"user_id": "u1"})

    assert len(fake.queries) == 1 and len(fake.scrolls) == 0  # 语义检索，未降级 scroll
    assert res[0]["cause"] == "题目格式错误"
    assert res[0]["fix_strategy"] == "用标准模板"
    assert res[0]["query"] == "线性回归测验"
    assert fake.queries[0]["limit"] == 3
    assert fake.queries[0]["query_filter"] is not None  # ACL 已下推 qdrant


@pytest.mark.asyncio
async def test_recall_degrades_to_scroll(monkeypatch):
    """embedding 不可用 → 降级 scroll（保留近 N 条召回，不空转）。"""
    monkeypatch.setattr(emb, "embed_query", _boom_embed)
    point = _Point({"user_id": "u1", "task_type": "doc", "cause": "降级召回的经验"})
    fake = _FakeQdrant(scroll_points=[point])

    res = await recall_reflections(qdrant=fake, task_type="", query="任意目标", acl={"user_id": "u1"})

    assert len(fake.scrolls) == 1 and len(fake.queries) == 0  # 走 scroll 降级
    assert res[0]["cause"] == "降级召回的经验"


@pytest.mark.asyncio
async def test_recall_acl_filters_other_users(monkeypatch):
    """跨 user_id 的经验被 ACL 兜底过滤（即便 qdrant 侧过滤被绕过也不泄漏）。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    fake = _FakeQdrant(
        hits=[
            _Point({"user_id": "u2", "task_type": "quiz", "cause": "别人的经验"}),
            _Point({"user_id": "u1", "task_type": "quiz", "cause": "我的经验"}),
        ]
    )

    res = await recall_reflections(qdrant=fake, task_type="", query="目标", acl={"user_id": "u1"})

    causes = [r["cause"] for r in res]
    assert "我的经验" in causes
    assert "别人的经验" not in causes


@pytest.mark.asyncio
async def test_recall_returns_empty_when_qdrant_none():
    res = await recall_reflections(qdrant=None, task_type="", query="x", acl={"user_id": "u1"})
    assert res == []


@pytest.mark.asyncio
async def test_recall_empty_query_skips_semantic(monkeypatch):
    """query 为空 → 不做无意义语义检索，直接降级 scroll。"""
    called = {"n": 0}

    def spy(q):
        called["n"] += 1
        return [0.1] * emb.EMBED_DIM

    monkeypatch.setattr(emb, "embed_query", spy)
    fake = _FakeQdrant(scroll_points=[])

    res = await recall_reflections(qdrant=fake, task_type="", query="", acl={"user_id": "u1"})

    assert called["n"] == 0  # 空 query 未触发 embed
    assert len(fake.scrolls) == 1
    assert res == []


# ---------------------------------------------------------------- enable_rag 门控（kill-switch）


@pytest.mark.asyncio
async def test_write_skips_qdrant_when_rag_disabled(monkeypatch):
    """enable_rag=False → 写入不触发 embedding、不写向量库（仅 PG 持久化），与 retrieve 门控一致。"""
    import reflexlearn.memory.reflexion as rfx

    class _S:
        enable_rag = False

    monkeypatch.setattr(rfx, "get_settings", lambda: _S())
    called = {"n": 0}

    def spy(texts):
        called["n"] += 1
        return [[0.1] * emb.EMBED_DIM]

    monkeypatch.setattr(emb, "embed_documents", spy)
    fake = _FakeQdrant()

    ok = await write_reflection(pg_pool=None, qdrant=fake, reflection=_reflection(), user_id="u1")

    assert ok is False
    assert called["n"] == 0  # RAG 关闭未触发 embedding（无谓加载模型）
    assert fake.upserts == []


@pytest.mark.asyncio
async def test_recall_skips_semantic_when_rag_disabled(monkeypatch):
    """enable_rag=False → 召回跳过语义、降级 scroll，不触发 embedding。"""
    import reflexlearn.memory.reflexion as rfx

    class _S:
        enable_rag = False

    monkeypatch.setattr(rfx, "get_settings", lambda: _S())
    called = {"n": 0}

    def spy(q):
        called["n"] += 1
        return [0.1] * emb.EMBED_DIM

    monkeypatch.setattr(emb, "embed_query", spy)
    point = _Point({"user_id": "u1", "task_type": "doc", "cause": "scroll 兜底经验"})
    fake = _FakeQdrant(scroll_points=[point])

    res = await recall_reflections(qdrant=fake, task_type="", query="任意", acl={"user_id": "u1"}, limit=2)

    assert called["n"] == 0  # RAG 关闭未触发 embedding
    assert len(fake.scrolls) == 1 and len(fake.queries) == 0
    assert res[0]["cause"] == "scroll 兜底经验"
