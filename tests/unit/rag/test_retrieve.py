from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
import reflexlearn.skills.retrieve as retr
from reflexlearn.rag.retrieval.keyword import KeywordIndex
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.retrieve import RetrieveSkill


def _ctx() -> SkillContext:
    return SkillContext(
        user_id="u1",
        acl={"user_id": "u1", "tenant_id": "default", "visibility": ["public"]},
        task_id="t1",
    )


class _Hit:
    def __init__(self, id, score, payload):
        self.id = id
        self.score = score
        self.payload = payload


class _QResp:
    def __init__(self, points):
        self.points = points


class _Point:
    def __init__(self, id, payload):
        self.id = id
        self.payload = payload


class _FakeQdrant:
    """同时支持 query_points(语义) 与 scroll(关键词 BM25 建索引)。"""

    def __init__(self, hits=None, scroll_points=None):
        self._hits = hits or []
        self._scroll = scroll_points or []
        self.searched: list[dict] = []

    async def query_points(self, **kwargs):
        self.searched.append(kwargs)
        return _QResp(self._hits)

    async def scroll(self, **kwargs):
        return self._scroll, None


def _kb_pts():
    # 4 文档让 BM25 IDF 正常（真实知识库几十 chunk）
    return [
        _Point("id1", {"content": "线性回归用最小二乘法求解参数", "source": "lr.md",
                       "visibility": "public", "source_trust": 0.9}),
        _Point("id2", {"content": "梯度下降通过迭代最小化损失函数", "source": "gd.md",
                       "visibility": "public", "source_trust": 0.8}),
        _Point("id3", {"content": "过拟合指模型在训练集表现好测试集差", "source": "of.md",
                       "visibility": "public", "source_trust": 0.7}),
        _Point("id4", {"content": "神经网络由多层神经元经前向传播构成", "source": "nn.md",
                       "visibility": "public", "source_trust": 0.6}),
    ]


@pytest.fixture(autouse=True)
def _reset_kw():
    KeywordIndex.invalidate()
    yield
    KeywordIndex.invalidate()


@pytest.mark.asyncio
async def test_hybrid_returns_mapped_chunks(monkeypatch):
    """三路混合（默认语义+关键词）成功 → 返回契约字段齐全的真实 chunks。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    hits = [_Hit("id1", 0.92, {"content": "线性回归用最小二乘法求解", "source": "lr.md", "source_trust": 0.9})]
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant(hits, _kb_pts()))
    res = await RetrieveSkill().run({"query": "线性回归怎么求解"}, _ctx())
    assert res.ok
    assert res.data["chunks"]
    c = res.data["chunks"][0]
    assert set(c) >= {"chunk_id", "content", "source", "relevance_score"}
    assert c["source"] != "mock_knowledge_base"  # 真实检索而非 mock


@pytest.mark.asyncio
async def test_degrades_to_mock_when_all_routes_empty(monkeypatch):
    """embedding 可用但 qdrant 空命中 + scroll 空 → 所有路无果 → 退 mock。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant([], []))
    res = await RetrieveSkill().run({"query": "无命中"}, _ctx())
    assert res.data["chunks"][0]["source"] == "mock_knowledge_base"


@pytest.mark.asyncio
async def test_mock_when_rag_disabled(monkeypatch):
    """enable_rag=False → 强制 mock，不触发任何检索 / embedding。"""

    class _S:
        enable_rag = False
        enable_graph_retrieval = False
        enable_rerank = True
        knowledge_collection = "knowledge_chunks"
        retrieve_top_k = 5

    monkeypatch.setattr(retr, "get_settings", lambda: _S())
    called = {"n": 0}

    def spy(q):
        called["n"] += 1
        return [0.1] * emb.EMBED_DIM

    monkeypatch.setattr(emb, "embed_query", spy)
    res = await RetrieveSkill().run({"query": "x"}, _ctx())
    assert res.data["chunks"][0]["source"] == "mock_knowledge_base"
    assert called["n"] == 0  # RAG 关闭，未触发检索


@pytest.mark.asyncio
async def test_degrades_to_mock_on_ragservice_error(monkeypatch):
    """RAGService.retrieve 抛 → _hybrid_search 捕获 → 退 mock，不抛。"""

    async def boom(self, *a, **k):
        raise RuntimeError("rag broken")

    monkeypatch.setattr("reflexlearn.rag.service.RAGService.retrieve", boom)
    res = await RetrieveSkill().run({"query": "线性回归"}, _ctx())
    assert res.ok
    assert res.data["chunks"][0]["source"] == "mock_knowledge_base"


@pytest.mark.asyncio
async def test_embedding_down_keyword_still_serves(monkeypatch):
    """embedding 不可用（conftest 拦）但 keyword 有数据 → 返回 keyword 结果（非 mock），体现混合检索韧性。"""
    # 不 monkeypatch embed_query → 走 conftest 守卫，embed_query 抛 EmbeddingUnavailable
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant([], _kb_pts()))
    res = await RetrieveSkill().run({"query": "线性回归"}, _ctx())
    assert res.ok
    assert res.data["chunks"]
    assert res.data["chunks"][0]["source"] != "mock_knowledge_base"
