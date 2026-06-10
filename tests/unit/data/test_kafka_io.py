"""M4-C Kafka 增量单测：注入假 producer（aiokafka 已装但**绝不真连 broker**，否则超时卡死），
覆盖事件编解码 / 投递成功·降级 / enqueue 协调 / 消费 handle_event / route enable_kafka 分流与降级。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import reflexlearn.api.routes.knowledge as kn
import reflexlearn.common.db as db
import reflexlearn.common.embedding as emb
from reflexlearn.api.app import create_app
from reflexlearn.data_engineering import kafka_io
from reflexlearn.data_engineering.events import (
    EVENT_DOC_ADDED,
    TOPIC_KNOWLEDGE_CHANGES,
    KnowledgeEvent,
    build_doc_event,
    decode_payload_raw,
)
from reflexlearn.data_engineering.ingest import IngestResult


class _FakeProducer:
    def __init__(self, boom: bool = False):
        self.sent: list[tuple] = []
        self._boom = boom

    async def send_and_wait(self, topic, *, key, value):
        if self._boom:
            raise RuntimeError("broker down")
        self.sent.append((topic, key, value))


class _FakeQdrant:
    def __init__(self):
        self.upserts: list[dict] = []

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs)


class _SettingsKafkaOn:
    enable_kafka = True
    enable_upload_quarantine = False  # 本组只测 Kafka 分流；隔离区由 test_upload_quarantine 覆盖
    max_upload_bytes = 10 * 1024 * 1024
    allowed_upload_extensions = "pdf,docx,pptx,html,htm,md,txt"
    allowed_upload_mime_types = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
        "text/html,text/markdown,text/plain"
    )


def _fake_vectors(texts):
    return [[0.1] * emb.EMBED_DIM for _ in texts]


def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "reflexlearn-admin"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(autouse=True)
def _reset_keyword():
    from reflexlearn.rag.retrieval.keyword import KeywordIndex

    KeywordIndex.invalidate()
    yield
    KeywordIndex.invalidate()


# ---------- 事件编解码 ----------
def test_build_event_roundtrip():
    ev = build_doc_event(doc_id="d1", filename="ml.md", raw=b"hello", course_id="c1", tenant_id="t1")
    assert ev.event_type == EVENT_DOC_ADDED and ev.doc_id == "d1" and ev.tenant_id == "t1"
    assert decode_payload_raw(ev) == b"hello"
    # JSON 序列化往返（消费端 model_validate_json 走这条）
    ev2 = KnowledgeEvent.model_validate_json(ev.model_dump_json())
    assert decode_payload_raw(ev2) == b"hello"
    assert ev2.payload["filename"] == "ml.md" and ev2.payload["course_id"] == "c1"


# ---------- publish_event ----------
@pytest.mark.asyncio
async def test_publish_event_success():
    p = _FakeProducer()
    ev = build_doc_event(doc_id="d1", filename="x.md", raw=b"x")
    assert await kafka_io.publish_event(ev, producer=p) is True
    assert p.sent and p.sent[0][0] == TOPIC_KNOWLEDGE_CHANGES
    assert p.sent[0][1] == b"d1"  # key = doc_id（同文档路由同分区，保顺序）


@pytest.mark.asyncio
async def test_publish_event_broker_down_degrades():
    p = _FakeProducer(boom=True)
    ev = build_doc_event(doc_id="d1", filename="x.md", raw=b"x")
    assert await kafka_io.publish_event(ev, producer=p) is False  # 不抛错，降级


# ---------- enqueue_document ----------
@pytest.mark.asyncio
async def test_enqueue_document_success():
    out = await kafka_io.enqueue_document(
        doc_id="d1", filename="x.md", raw=b"x", producer=_FakeProducer()
    )
    assert out == {"status": "queued", "doc_id": "d1", "event_type": EVENT_DOC_ADDED}


@pytest.mark.asyncio
async def test_enqueue_document_broker_down_returns_none():
    out = await kafka_io.enqueue_document(
        doc_id="d1", filename="x.md", raw=b"x", producer=_FakeProducer(boom=True)
    )
    assert out is None  # route 据此降级同步


# ---------- handle_event（消费端 → ingest_document）----------
@pytest.mark.asyncio
async def test_handle_event_doc_added_ingests(monkeypatch):
    monkeypatch.setattr(emb, "embed_documents", _fake_vectors)
    ev = build_doc_event(
        doc_id="d1", filename="ml.md",
        raw="# 标题\n\n第一段足够长的正文用于分块入库测试。\n\n第二段继续测试消费链路。".encode(),
        tenant_id="default",
    )
    qd = _FakeQdrant()
    res = await kafka_io.handle_event(ev, qdrant=qd, pg_pool=None, neo4j=None)
    assert res is not None and res.chunks > 0
    assert res.qdrant_written == res.chunks
    # payload 还原后经唯一写入口入库，与上传 API 同链路
    assert qd.upserts[0]["points"][0].payload["source"] == "ml.md"


@pytest.mark.asyncio
async def test_handle_event_doc_deleted_noop():
    ev = KnowledgeEvent(event_type="doc_deleted", doc_id="d1")
    res = await kafka_io.handle_event(ev, qdrant=None, pg_pool=None)
    assert res is None


# ---------- route enable_kafka 分流 ----------
def test_route_kafka_enabled_queues(monkeypatch):
    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    monkeypatch.setattr(kn, "get_settings", lambda: _SettingsKafkaOn())

    async def fake_enqueue(**kwargs):
        return {"status": "queued", "doc_id": "dq", "event_type": "doc_added"}

    monkeypatch.setattr("reflexlearn.data_engineering.kafka_io.enqueue_document", fake_enqueue)
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("ml.md", b"# T\n\nbody", "text/markdown")},
        data={"course_id": "c1"},
        headers=auth_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued" and resp.json()["doc_id"] == "dq"


def test_route_kafka_down_falls_back_sync(monkeypatch):
    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    monkeypatch.setattr(kn, "get_settings", lambda: _SettingsKafkaOn())

    async def fake_enqueue(**kwargs):
        return None  # broker 不可用

    monkeypatch.setattr("reflexlearn.data_engineering.kafka_io.enqueue_document", fake_enqueue)

    async def fake_ingest(**kwargs):
        return IngestResult(doc_id="dsync", title="t", format="md", status="ok")

    monkeypatch.setattr(kn, "ingest_document", fake_ingest)
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("ml.md", b"# T\n\nbody", "text/markdown")},
        data={"course_id": "c1"},
        headers=auth_headers(client),
    )
    assert resp.status_code == 200
    assert resp.json()["doc_id"] == "dsync"  # broker 挂 → 降级走同步链路
