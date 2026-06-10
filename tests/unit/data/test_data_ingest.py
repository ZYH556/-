"""核心写链路单测：注入假 qdrant / pg（仿 memory.reflexion 测试范式），覆盖成功路径与每条降级路径。

embedding 走 monkeypatch emb.embed_documents 注入假向量（conftest 守卫拦真实 _get_model）；
qdrant / pg 用假对象注入，绝不触发真实连接（conftest 不拦 pg，故必须注入而非函数内自取）。
"""
from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.data_engineering.ingest import ingest_document

MD = "# 标题\n\n这是第一段内容用于测试分块与入库流程。\n\n这是第二段内容继续测试写链路。".encode()


class _FakeQdrant:
    def __init__(self):
        self.upserts: list[dict] = []

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs)


class _FakePgConn:
    def __init__(self):
        self.calls: list[tuple] = []

    async def execute(self, *args, **kwargs):
        self.calls.append(args)
        return "INSERT 0 1"


class _AcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class _FakePgPool:
    def __init__(self):
        self.conn = _FakePgConn()

    def acquire(self):
        return _AcquireCtx(self.conn)


def _fake_vectors(texts):
    return [[0.1] * emb.EMBED_DIM for _ in texts]


@pytest.fixture(autouse=True)
def _reset_keyword():
    from reflexlearn.rag.retrieval.keyword import KeywordIndex

    KeywordIndex.invalidate()
    yield
    KeywordIndex.invalidate()


@pytest.mark.asyncio
async def test_ingest_writes_qdrant_and_pg(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    qd, pg = _FakeQdrant(), _FakePgPool()
    res = await ingest_document(
        filename="ml.md", raw=MD, course_id="ml-101", user_id="u1",
        tenant_id="default", visibility="public", qdrant=qd, pg_pool=pg,
    )
    assert res.status == "ok"
    assert res.chunks > 0
    assert res.embedded == res.chunks
    assert res.qdrant_written == res.chunks
    assert res.pg_written is True

    p0 = qd.upserts[0]["points"][0]
    assert p0.payload["source"] == "ml.md"
    assert p0.payload["tenant_id"] == "default"
    assert p0.payload["visibility"] == "public"
    assert p0.payload["course_id"] == "ml-101"
    assert p0.payload["user_id"] == "u1"
    assert p0.payload["source_trust"] == 0.7
    assert p0.payload["content"]
    assert len(p0.vector) == emb.EMBED_DIM
    # PG 登记的是 documents 表（execute(sql, $1=doc_id, ...) → args[1] 为 doc_id）
    assert pg.conn.calls and pg.conn.calls[0][1] == res.doc_id


@pytest.mark.asyncio
async def test_ingest_point_id_idempotent(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    qd1, qd2 = _FakeQdrant(), _FakeQdrant()
    r1 = await ingest_document(filename="ml.md", raw=MD, course_id="ml-101", qdrant=qd1, pg_pool=None)
    r2 = await ingest_document(filename="ml.md", raw=MD, course_id="ml-101", qdrant=qd2, pg_pool=None)
    assert r1.doc_id == r2.doc_id
    ids1 = [p.id for p in qd1.upserts[0]["points"]]
    ids2 = [p.id for p in qd2.upserts[0]["points"]]
    assert ids1 == ids2  # 同 doc 同 idx → 同 point id（幂等覆盖）


@pytest.mark.asyncio
async def test_ingest_embedding_unavailable_degrades(monkeypatch):
    def boom(texts):
        raise emb.EmbeddingUnavailable("no model")

    monkeypatch.setattr(emb, "embed_documents", boom)
    qd, pg = _FakeQdrant(), _FakePgPool()
    res = await ingest_document(filename="ml.md", raw=MD, qdrant=qd, pg_pool=pg)
    assert res.embedded == 0
    assert res.qdrant_written == 0
    assert qd.upserts == []  # 绝不写零向量
    assert res.pg_written is True  # PG 仍登记
    assert any("embedding" in d for d in res.degraded)
    assert res.status == "ok"


@pytest.mark.asyncio
async def test_ingest_qdrant_none_degrades(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    res = await ingest_document(filename="ml.md", raw=MD, qdrant=None, pg_pool=_FakePgPool())
    assert res.qdrant_written == 0
    assert any("qdrant" in d for d in res.degraded)
    assert res.pg_written is True


@pytest.mark.asyncio
async def test_ingest_pg_none_degrades(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    qd = _FakeQdrant()
    res = await ingest_document(filename="ml.md", raw=MD, qdrant=qd, pg_pool=None)
    assert res.pg_written is False
    assert any("pg" in d for d in res.degraded)
    assert res.qdrant_written > 0
    assert res.status == "ok"


@pytest.mark.asyncio
async def test_ingest_parse_unavailable_degrades():
    res = await ingest_document(filename="x.xyz", raw=b"data", qdrant=None, pg_pool=None)
    assert res.status == "degraded"
    assert res.chunks == 0
    assert any("parse" in d for d in res.degraded)


@pytest.mark.asyncio
async def test_ingest_empty_doc():
    res = await ingest_document(filename="empty.txt", raw=b"   ", qdrant=None, pg_pool=None)
    assert res.status == "empty"
    assert res.chunks == 0


@pytest.mark.asyncio
async def test_ingest_invalidates_keyword(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    from reflexlearn.rag.retrieval.keyword import KeywordIndex

    calls = []
    monkeypatch.setattr(KeywordIndex, "invalidate", classmethod(lambda cls: calls.append(1)))
    await ingest_document(filename="ml.md", raw=MD, qdrant=_FakeQdrant(), pg_pool=None)
    assert len(calls) >= 1  # 写入后失效关键词索引（写→读闭环）


@pytest.mark.asyncio
async def test_ingest_rag_disabled_skips_embedding(monkeypatch):
    import reflexlearn.data_engineering.ingest as ing

    class _S:
        enable_rag = False
        enable_contextual = False
        contextual_max_chunks = 50
        knowledge_collection = "knowledge_chunks"
        enable_graph_build = False

    monkeypatch.setattr(ing, "get_settings", lambda: _S())
    called = {"n": 0}

    def spy(texts):
        called["n"] += 1
        return _fake_vectors(texts)

    monkeypatch.setattr(emb, "embed_documents", spy)
    res = await ingest_document(filename="ml.md", raw=MD, qdrant=_FakeQdrant(), pg_pool=_FakePgPool())
    assert called["n"] == 0  # RAG 关闭不触发 embedding
    assert res.embedded == 0
    assert any("rag_disabled" in d for d in res.degraded)


@pytest.mark.asyncio
async def test_contextual_on_llm_unavailable_falls_back(monkeypatch):
    """contextual 开启但 LLM 不可用 → 逐块回退原文，标注 degraded，仍正常入库。"""
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    import reflexlearn.llm_gateway.gateway as gw_mod

    async def boom_complete(self, **kwargs):
        raise RuntimeError("llm_no_api_key")

    monkeypatch.setattr(gw_mod.LLMGateway, "complete", boom_complete)
    qd = _FakeQdrant()
    res = await ingest_document(
        filename="ml.md", raw=MD, qdrant=qd, pg_pool=None, enable_contextual=True
    )
    assert res.contextual is False
    assert any("contextual" in d for d in res.degraded)
    assert res.qdrant_written > 0


@pytest.mark.asyncio
async def test_contextual_on_llm_available_prefixes_embedding(monkeypatch):
    """contextual 开启且 LLM 可用 → 摘要前缀进 embedding，但 payload.content 保留原文。"""
    import reflexlearn.llm_gateway.gateway as gw_mod
    from reflexlearn.llm_gateway.gateway import Completion

    async def fake_complete(self, **kwargs):
        return Completion(text="本段讲线性回归")

    monkeypatch.setattr(gw_mod.LLMGateway, "complete", fake_complete)
    captured = {}

    def spy_embed(texts):
        captured["texts"] = texts
        return _fake_vectors(texts)

    monkeypatch.setattr(emb, "embed_documents", spy_embed)
    qd = _FakeQdrant()
    res = await ingest_document(
        filename="ml.md", raw=MD, qdrant=qd, pg_pool=None, enable_contextual=True
    )
    assert res.contextual is True
    assert any("本段讲线性回归" in t for t in captured["texts"])  # 摘要进了向量
    contents = [p.payload["content"] for p in qd.upserts[0]["points"]]
    assert all("本段讲线性回归" not in c for c in contents)  # 原文入库（检索展示用）
