from __future__ import annotations

import asyncio

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.rag.retrieval.keyword import KeywordIndex
from reflexlearn.rag.service import RAGService


# —— Fake Qdrant：同时支持 query_points(语义) 与 scroll(关键词) ——
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
    def __init__(self, hits=None, scroll_points=None, fail_scroll=False):
        self._hits = hits or []
        self._scroll = scroll_points or []
        self._fail_scroll = fail_scroll

    async def query_points(self, **kw):
        return _QResp(self._hits)

    async def scroll(self, **kw):
        if self._fail_scroll:
            raise RuntimeError("scroll boom")
        return self._scroll, None


# —— Fake Neo4j async driver ——
class _Rec:
    def __init__(self, d):
        self._d = d

    def data(self):
        return self._d


class _RecStream:
    def __init__(self, rows):
        self._rows = [_Rec(r) for r in rows]

    def __aiter__(self):
        async def gen():
            for r in self._rows:
                yield r

        return gen()


class _Session:
    def __init__(self, neo4j):
        self._neo4j = neo4j

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def run(self, cypher, **p):
        if "RETURN c.name AS name" in cypher:
            return _RecStream([{"name": n} for n in self._neo4j.concept_names])
        return _RecStream(self._neo4j.expand_rows)


class FakeNeo4j:
    def __init__(self, concept_names, expand_rows):
        self.concept_names = concept_names
        self.expand_rows = expand_rows

    def session(self):
        return _Session(self)


class BoomNeo4j:
    def session(self):
        raise RuntimeError("neo4j down")


class _IdentityReranker:
    """保持 RRF 顺序，便于断言（真 reranker 在活体验证）。"""

    def rerank(self, query, chunks):
        return chunks


class _FakeSettings:
    def __init__(self, graph=True, rerank=True):
        self.enable_graph_retrieval = graph
        self.enable_rerank = rerank
        self.retrieve_top_k = 5
        self.knowledge_collection = "knowledge_chunks"


def _scroll_pts():
    # 4 个文档对应真实 4 个 ML 主题：让 BM25 的 IDF=log((N-df+0.5)/(df+0.5)) 为正
    # （N=2 时 df=1 会使 IDF=0，是小语料退化；真实知识库几十 chunk 不出现此问题）
    return [
        _Point("id1", {"content": "线性回归用最小二乘法求解参数", "source": "lr.md",
                       "visibility": "public", "source_trust": 0.9}),
        _Point("id2", {"content": "梯度下降通过迭代最小化损失函数", "source": "gd.md",
                       "visibility": "public", "source_trust": 0.8}),
        _Point("id3", {"content": "过拟合指模型在训练集表现好而测试集表现差", "source": "of.md",
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
async def test_all_three_routes_fuse(monkeypatch):
    """三路全可用：semantic + keyword + graph 都进 routes_used，融合后有结果。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    hits = [_Hit("id1", 0.9, {"content": "线性回归内容", "source": "lr.md", "source_trust": 0.9})]
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant(hits, _scroll_pts()))
    neo = FakeNeo4j(["线性回归", "梯度下降"], [{"name": "梯度下降", "desc": "迭代"}])
    svc = RAGService(neo4j=neo, reranker=_IdentityReranker(), settings=_FakeSettings())
    res = await svc.retrieve("线性回归怎么求解", acl={"tenant_id": "default"}, query_type="concept_dependency")
    assert "semantic" in res.routes_used
    assert "keyword" in res.routes_used
    assert "graph" in res.routes_used
    assert res.chunks


@pytest.mark.asyncio
async def test_graph_gate_off_skips_graph(monkeypatch):
    """enable_graph_retrieval=False → 图路不执行。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([], _scroll_pts()))
    neo = FakeNeo4j(["线性回归"], [{"name": "梯度下降", "desc": "d"}])
    svc = RAGService(neo4j=neo, reranker=_IdentityReranker(), settings=_FakeSettings(graph=False))
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"}, query_type="concept_dependency")
    assert "graph" not in res.routes_used


@pytest.mark.asyncio
async def test_neo4j_error_skips_graph_not_raise(monkeypatch):
    """Neo4j 连不上 → 图路跳过，其余路仍出结果，不抛。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([], _scroll_pts()))
    svc = RAGService(neo4j=BoomNeo4j(), reranker=_IdentityReranker(), settings=_FakeSettings())
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"}, query_type="concept_dependency")
    assert "graph" not in res.routes_used
    assert res.chunks  # keyword 仍有结果


@pytest.mark.asyncio
async def test_rerank_unavailable_falls_back_to_weighted(monkeypatch):
    """reranker 不可用（conftest 拦真模型，且不注入）→ 退 weighted_sort，仍有结果不抛。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([], _scroll_pts()))
    svc = RAGService(settings=_FakeSettings(graph=False))  # reranker=None -> 用 ranking.rerank（被 conftest 拦）
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"})
    assert res.chunks


@pytest.mark.asyncio
async def test_keyword_index_fail_skips_keyword(monkeypatch):
    """BM25 索引构建失败（scroll 抛）→ 关键词路跳过，语义路仍工作。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    hits = [_Hit("id1", 0.9, {"content": "线性回归内容", "source": "lr.md", "source_trust": 0.9})]
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant(hits, fail_scroll=True))
    svc = RAGService(reranker=_IdentityReranker(), settings=_FakeSettings(graph=False))
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"}, query_type="default")
    assert "keyword" not in res.routes_used
    assert "semantic" in res.routes_used


@pytest.mark.asyncio
async def test_embedding_unavailable_graph_keyword_still_work(monkeypatch):
    """embedding 不可用（conftest 拦 _get_model）→ 语义路跳过，但关键词/图谱仍工作。
    这验证「图扩展不触发 embedding」铁律。"""
    # 不 monkeypatch embed_query → 走 conftest 守卫，embed_query 抛 EmbeddingUnavailable
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([], _scroll_pts()))
    neo = FakeNeo4j(["线性回归", "梯度下降"], [{"name": "梯度下降", "desc": "d"}])
    svc = RAGService(neo4j=neo, reranker=_IdentityReranker(), settings=_FakeSettings())
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"}, query_type="concept_dependency")
    assert "semantic" not in res.routes_used
    assert "keyword" in res.routes_used or "graph" in res.routes_used
    assert res.chunks


@pytest.mark.asyncio
async def test_all_routes_fail_returns_empty(monkeypatch):
    """全路失败（embedding 拦 + scroll 抛 + neo4j 抛）→ 空 chunks，不抛。"""
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([], fail_scroll=True))
    svc = RAGService(neo4j=BoomNeo4j(), reranker=_IdentityReranker(), settings=_FakeSettings())
    res = await svc.retrieve("线性回归", acl={"tenant_id": "default"}, query_type="concept_dependency")
    assert res.chunks == []


@pytest.mark.asyncio
async def test_concurrent_retrieve_keeps_event_loop_responsive(monkeypatch):
    """并发 retrieve（含同步 embedding/rerank）不应阻塞事件循环——fan-out 并行化根因守门。

    embed_query 用同步 time.sleep 模拟重 CPU；若仍同步调用会卡死 loop，并发 retrieve 期间
    probe 协程无法推进。修复后 embed/rerank 经 run_model 丢线程，probe 应能穿插完成。
    """
    import time as _t

    monkeypatch.setattr(emb, "embed_query", lambda q: (_t.sleep(0.15), [0.1] * emb.EMBED_DIM)[1])
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant",
                        lambda: _FakeQdrant([_Hit("id1", 0.9, {"content": "c", "source": "s"})], _scroll_pts()))
    svc = RAGService(reranker=_IdentityReranker(), settings=_FakeSettings(graph=False))

    progressed = 0

    async def probe():
        nonlocal progressed
        for _ in range(5):
            await asyncio.sleep(0.02)
            progressed += 1

    async def two_retrieves():
        await asyncio.gather(
            svc.retrieve("线性回归", acl={"tenant_id": "default"}),
            svc.retrieve("梯度下降", acl={"tenant_id": "default"}),
        )

    await asyncio.gather(two_retrieves(), probe())
    # 两次 retrieve 的同步 embed 串行约 0.3s；probe 若被阻塞则 progressed 会很小。
    assert progressed == 5
