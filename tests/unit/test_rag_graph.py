from __future__ import annotations

import pytest

from reflexlearn.rag.graph_retrieval import _extract_concepts, graph_expand
from reflexlearn.rag.schemas import ChunkMeta


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

    async def run(self, cypher, **params):
        self._neo4j.calls.append((cypher, params))
        if "RETURN c.name AS name" in cypher:  # _all_concept_names
            return _RecStream([{"name": n} for n in self._neo4j.concept_names])
        return _RecStream(self._neo4j.expand_rows)  # 扩展查询


class FakeNeo4j:
    def __init__(self, concept_names, expand_rows):
        self.concept_names = concept_names
        self.expand_rows = expand_rows
        self.calls: list = []

    def session(self):
        return _Session(self)

    async def close(self):
        pass


class FakeKW:
    def __init__(self, mapping):
        self._m = mapping  # concept_name -> [ChunkMeta]

    def search(self, query, top_k=5, acl=None):
        return list(self._m.get(query, []))


def test_extract_concepts_containment():
    assert "线性回归" in _extract_concepts("线性回归怎么求解参数", ["线性回归", "梯度下降"])
    assert _extract_concepts("完全无关的问题", ["线性回归"]) == []
    assert _extract_concepts("", ["线性回归"]) == []


@pytest.mark.asyncio
async def test_graph_expand_hits_via_keyword():
    """query 命中种子概念 → 图扩展 → keyword 命中 chunk（origin=graph）。全程不 embed。"""
    neo = FakeNeo4j(["线性回归", "梯度下降"], [{"name": "梯度下降", "desc": "迭代下降"}])
    kw = FakeKW({"梯度下降": [ChunkMeta(chunk_id="id2", content="梯度下降内容", source="gd.md")]})
    out = await graph_expand(neo, "线性回归怎么求解", {"tenant_id": "default"}, keyword_index=kw)
    assert out
    assert out[0].chunk_id == "id2"
    assert out[0].origin == "graph"


@pytest.mark.asyncio
async def test_graph_expand_concept_fallback_without_keyword():
    """无 keyword_index → 扩展概念作低分占位 chunk。"""
    neo = FakeNeo4j(["线性回归", "梯度下降"], [{"name": "梯度下降", "desc": "沿梯度下降"}])
    out = await graph_expand(neo, "线性回归", {"tenant_id": "default"}, keyword_index=None)
    assert out[0].chunk_id == "graph::梯度下降"
    assert out[0].origin == "graph"
    assert "梯度下降" in out[0].content


@pytest.mark.asyncio
async def test_graph_expand_no_seed_returns_empty():
    neo = FakeNeo4j(["线性回归"], [])
    out = await graph_expand(neo, "完全无关的问题xyz", {"tenant_id": "default"})
    assert out == []


@pytest.mark.asyncio
async def test_graph_expand_neo4j_error_returns_empty():
    """Neo4j 异常 → 返回 []（service 视为该路无结果，不抛）。"""

    class BoomNeo:
        def session(self):
            raise RuntimeError("neo4j down")

    out = await graph_expand(BoomNeo(), "线性回归", {"tenant_id": "default"})
    assert out == []
