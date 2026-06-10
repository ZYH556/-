"""M4-B 图谱构建单测：注入假 neo4j / 假 gateway（仿 test_data_ingest 范式），覆盖抽取/MERGE/编排/降级。

conftest **不拦 get_neo4j、不拦 gateway**，故全部注入假对象：既测成功路径，又不触发真实 neo4j 连接 /
真实 LLM 外呼。集成测试（ingest_document）用 monkeypatch LLMGateway.complete（ingest 内部自构造网关）。
"""
from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.data_engineering.graph_build import (
    ExtractedConcept,
    ExtractedRelation,
    GraphExtraction,
    _loads_lenient,
    _sanitize,
    build_graph,
    extract_concepts,
    merge_into_neo4j,
)
from reflexlearn.data_engineering.ingest import ingest_document
from reflexlearn.llm_gateway.gateway import Completion

MD = "# 线性回归\n\n线性回归是基础监督学习算法。\n\n梯度下降用于优化参数。".encode()
_VALID_JSON = (
    '{"concepts":[{"name":"线性回归","description":"基础监督学习","difficulty":0.3},'
    '{"name":"梯度下降","description":"优化算法","difficulty":0.4}],'
    '"relations":[{"source":"线性回归","target":"梯度下降","type":"PREREQUISITE_OF"}]}'
)


# ---------- 假对象 ----------
class _Chunk:
    def __init__(self, text: str, idx: int = 0, heading: str = ""):
        self.text, self.idx, self.heading = text, idx, heading


class _FakeNeo4jSession:
    def __init__(self, sink: list):
        self.sink = sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self, cypher, **params):
        self.sink.append((cypher, params))


class _FakeNeo4j:
    def __init__(self):
        self.runs: list[tuple] = []

    def session(self):
        return _FakeNeo4jSession(self.runs)


class _BoomNeo4jSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self, *a, **k):
        raise RuntimeError("neo4j conn refused")


class _BoomNeo4j:
    def session(self):
        return _BoomNeo4jSession()


class _FakeGateway:
    def __init__(self, text: str):
        self._text = text

    async def complete(self, **kwargs):
        return Completion(text=self._text)


class _BoomGateway:
    async def complete(self, **kwargs):
        raise RuntimeError("llm_no_api_key")


class _FakeSettings:
    graph_extract_max_chars = 8000


# ---------- ingest 集成用假对象（仿 test_data_ingest）----------
class _FakeQdrant:
    def __init__(self):
        self.upserts: list[dict] = []

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs)


def _fake_vectors(texts):
    return [[0.1] * emb.EMBED_DIM for _ in texts]


@pytest.fixture(autouse=True)
def _reset_keyword():
    from reflexlearn.rag.retrieval.keyword import KeywordIndex

    KeywordIndex.invalidate()
    yield
    KeywordIndex.invalidate()


# ---------- _loads_lenient ----------
def test_loads_lenient_strips_fence():
    assert _loads_lenient('```json\n{"concepts":[],"relations":[]}\n```') == {
        "concepts": [],
        "relations": [],
    }
    assert _loads_lenient('好的，结果是 {"a":1} 以上') == {"a": 1}


# ---------- _sanitize ----------
def test_sanitize_dedup_clamp_and_filter():
    ext = GraphExtraction(
        concepts=[
            ExtractedConcept(name="A", difficulty=2.0),   # clamp → 1.0
            ExtractedConcept(name="A", difficulty=0.1),   # 重复 → 丢
            ExtractedConcept(name="  ", difficulty=0.5),  # 空名 → 丢
            ExtractedConcept(name="B", difficulty=-1.0),  # clamp → 0.0
        ],
        relations=[
            ExtractedRelation(source="A", target="B", type="PREREQUISITE_OF"),
            ExtractedRelation(source="A", target="A", type="RELATED_TO"),   # 自环 → 丢
            ExtractedRelation(source="A", target="C", type="RELATED_TO"),   # 悬空 C → 丢
            ExtractedRelation(source="A", target="B", type="weird"),        # type 归一 RELATED_TO
        ],
    )
    s = _sanitize(ext)
    assert [c.name for c in s.concepts] == ["A", "B"]
    assert s.concepts[0].difficulty == 1.0 and s.concepts[1].difficulty == 0.0
    triples = {(r.source, r.target, r.type) for r in s.relations}
    assert triples == {("A", "B", "PREREQUISITE_OF"), ("A", "B", "RELATED_TO")}


# ---------- extract_concepts ----------
@pytest.mark.asyncio
async def test_extract_success():
    ext, note = await extract_concepts(
        [_Chunk("线性回归与梯度下降")], "ML", _FakeSettings(), gateway=_FakeGateway(_VALID_JSON)
    )
    assert note == ""
    assert [c.name for c in ext.concepts] == ["线性回归", "梯度下降"]
    assert ext.relations[0].type == "PREREQUISITE_OF"


@pytest.mark.asyncio
async def test_extract_with_fence():
    ext, note = await extract_concepts(
        [_Chunk("内容")], "ML", _FakeSettings(),
        gateway=_FakeGateway(f"```json\n{_VALID_JSON}\n```"),
    )
    assert note == "" and len(ext.concepts) == 2


@pytest.mark.asyncio
async def test_extract_llm_unavailable():
    ext, note = await extract_concepts(
        [_Chunk("内容")], "ML", _FakeSettings(), gateway=_BoomGateway()
    )
    assert ext is None and "llm" in note


@pytest.mark.asyncio
async def test_extract_bad_json():
    ext, note = await extract_concepts(
        [_Chunk("内容")], "ML", _FakeSettings(), gateway=_FakeGateway("抱歉无法抽取")
    )
    assert ext is None and "parse" in note


@pytest.mark.asyncio
async def test_extract_empty_text():
    ext, note = await extract_concepts([_Chunk("   ")], "ML", _FakeSettings(), gateway=_FakeGateway(_VALID_JSON))
    assert ext is None and note == "graph:empty_text"


# ---------- merge_into_neo4j ----------
@pytest.mark.asyncio
async def test_merge_writes_concepts_and_relations():
    ext = GraphExtraction(
        concepts=[
            ExtractedConcept(name="线性回归", description="d", difficulty=0.3),
            ExtractedConcept(name="梯度下降", description="d2", difficulty=0.4),
        ],
        relations=[
            ExtractedRelation(source="线性回归", target="梯度下降", type="PREREQUISITE_OF"),
            ExtractedRelation(source="线性回归", target="梯度下降", type="RELATED_TO"),
        ],
    )
    neo4j = _FakeNeo4j()
    nc, nr = await merge_into_neo4j(
        neo4j, ext, tenant_id="default", visibility="public", doc_id="doc1"
    )
    assert nc == 2 and nr == 2
    cyphers = [c for c, _ in neo4j.runs]
    assert sum("MERGE (n:Concept" in c for c in cyphers) == 2
    assert any("PREREQUISITE_OF" in c for c in cyphers)
    assert any("RELATED_TO" in c for c in cyphers)
    # 概念 MERGE 带 tenant/visibility（对齐 graph_retrieval 读侧 ACL：tenant_id OR visibility=public）
    cparams = [p for c, p in neo4j.runs if "MERGE (n:Concept" in c]
    assert cparams[0]["tid"] == "default" and cparams[0]["vis"] == "public"
    assert cparams[0]["doc"] == "doc1"


# ---------- build_graph 编排四态 ----------
@pytest.mark.asyncio
async def test_build_graph_neo4j_none_skips():
    status, nc, nr, notes = await build_graph(
        chunks=[_Chunk("x")], doc_title="T", doc_id="d", tenant_id="default",
        visibility="public", neo4j=None, settings=_FakeSettings(),
    )
    assert status == "skipped" and nc == 0
    assert any("neo4j_unavailable" in n for n in notes)


@pytest.mark.asyncio
async def test_build_graph_success():
    neo4j = _FakeNeo4j()
    status, nc, nr, notes = await build_graph(
        chunks=[_Chunk("线性回归")], doc_title="T", doc_id="d", tenant_id="default",
        visibility="public", neo4j=neo4j, settings=_FakeSettings(),
        gateway=_FakeGateway(_VALID_JSON),
    )
    assert status == "ok" and nc == 2 and nr == 1 and notes == []


@pytest.mark.asyncio
async def test_build_graph_llm_unavailable_skips():
    neo4j = _FakeNeo4j()
    status, nc, nr, notes = await build_graph(
        chunks=[_Chunk("x")], doc_title="T", doc_id="d", tenant_id="default",
        visibility="public", neo4j=neo4j, settings=_FakeSettings(), gateway=_BoomGateway(),
    )
    assert status == "skipped" and nc == 0
    assert neo4j.runs == []  # 抽不出 → 不写


@pytest.mark.asyncio
async def test_build_graph_merge_error_degrades():
    status, nc, nr, notes = await build_graph(
        chunks=[_Chunk("线性回归")], doc_title="T", doc_id="d", tenant_id="default",
        visibility="public", neo4j=_BoomNeo4j(), settings=_FakeSettings(),
        gateway=_FakeGateway(_VALID_JSON),
    )
    assert status == "degraded"
    assert any("merge" in n for n in notes)


# ---------- ingest_document 集成三态 ----------
@pytest.mark.asyncio
async def test_ingest_graph_build_success(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    import reflexlearn.llm_gateway.gateway as gw_mod

    async def fake_complete(self, **kwargs):
        return gw_mod.Completion(text=_VALID_JSON)

    monkeypatch.setattr(gw_mod.LLMGateway, "complete", fake_complete)
    neo4j = _FakeNeo4j()
    res = await ingest_document(
        filename="ml.md", raw=MD, qdrant=_FakeQdrant(), pg_pool=None,
        neo4j=neo4j, enable_graph_build=True,
    )
    assert res.graph == "ok"
    assert res.graph_concepts == 2 and res.graph_relations == 1
    assert any("MERGE (n:Concept" in c for c, _ in neo4j.runs)


@pytest.mark.asyncio
async def test_ingest_graph_disabled_by_default(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    res = await ingest_document(
        filename="ml.md", raw=MD, qdrant=_FakeQdrant(), pg_pool=None, neo4j=_FakeNeo4j()
    )
    assert res.graph == "disabled"
    assert res.graph_concepts == 0


@pytest.mark.asyncio
async def test_ingest_graph_neo4j_none_skips(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    res = await ingest_document(
        filename="ml.md", raw=MD, qdrant=_FakeQdrant(), pg_pool=None,
        neo4j=None, enable_graph_build=True,
    )
    assert res.graph == "skipped"
    assert any("neo4j_unavailable" in d for d in res.degraded)
