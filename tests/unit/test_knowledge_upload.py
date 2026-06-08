"""知识上传 API 单测：multipart 上传 → 200 + 结果契约；form 参数透传 ingest_document。

ingest_document 被 monkeypatch 为假实现（验证 API 层契约，不触碰真实写链路）；
db.get_pg_pool 被 monkeypatch 为返回 None（route 的 _safe_pg 不触发真实 asyncpg 连接）。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import reflexlearn.common.db as db
from reflexlearn.api.app import create_app
from reflexlearn.data_engineering.ingest import IngestResult


@pytest.fixture
def client(monkeypatch):
    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    return TestClient(create_app())


def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "reflexlearn-admin"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_upload_returns_result(client, monkeypatch):
    async def fake_ingest(**kwargs):
        return IngestResult(
            doc_id="d1", title="T", format="md", chunks=3,
            embedded=3, qdrant_written=3, pg_written=True, status="ok",
        )

    monkeypatch.setattr("reflexlearn.api.routes.knowledge.ingest_document", fake_ingest)
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("ml.md", b"# T\n\nbody", "text/markdown")},
        data={"course_id": "ml-101"},
        headers=auth_headers(client),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["doc_id"] == "d1"
    assert body["chunks"] == 3
    assert body["status"] == "ok"


def test_upload_passes_params(client, monkeypatch):
    captured = {}

    async def fake_ingest(**kwargs):
        captured.update(kwargs)
        return IngestResult(doc_id="d", title="t", format="md")

    monkeypatch.setattr("reflexlearn.api.routes.knowledge.ingest_document", fake_ingest)
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
        data={
            "course_id": "c1",
            "user_id": "attacker",
            "tenant_id": "evil",
            "visibility": "private",
            "enable_contextual": "true",
        },
        headers=auth_headers(client),
    )
    assert resp.status_code == 200
    assert captured["filename"] == "note.txt"
    assert captured["course_id"] == "c1"
    assert captured["user_id"] == "admin"
    assert captured["tenant_id"] == "default"
    assert captured["visibility"] == "private"
    assert captured["enable_contextual"] is True
    assert captured["raw"] == b"hello"
