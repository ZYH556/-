"""W3-D: 上传隔离区与扫描占位。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings
from reflexlearn.security.uploads import (
    ACCEPTED,
    QUARANTINED,
    UploadQuarantineStore,
    scan_upload,
)


@pytest.fixture(autouse=True)
def _no_pg(monkeypatch):
    import reflexlearn.common.db as db

    async def _none():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _none)


def _bearer():
    token = issue_token(CurrentUser(user_id="up1", tenant_id="default", role="student"), Settings())
    return {"Authorization": f"Bearer {token}"}


# —— scan_upload 单元 ——
def test_scan_allows_plain_markdown():
    assert scan_upload(raw=b"# Title\n\nbody text", extension="md") == []


def test_scan_rejects_executable_magic():
    assert "executable_content" in scan_upload(raw=b"MZ\x90\x00rest", extension="bin")


def test_scan_rejects_dangerous_html():
    assert "dangerous_html" in scan_upload(
        raw=b"<html><script>alert(1)</script></html>", extension="html"
    )


def test_scan_allows_clean_html():
    assert scan_upload(raw=b"<html><body><p>hello</p></body></html>", extension="html") == []


# —— UploadQuarantineStore 单元 ——
async def test_quarantine_register_and_mark():
    store = UploadQuarantineStore(pg_pool=None)
    obj = await store.register(
        user_id="u1",
        tenant_id="t1",
        original_name="a.md",
        raw=b"hello",
        content_type="text/markdown",
    )
    assert obj.status == QUARANTINED
    assert obj.sha256
    assert obj.size == 5
    await store.mark(obj, ACCEPTED)
    got = await store.get(obj.object_id)
    assert got is not None
    assert got.status == ACCEPTED


# —— API 集成 ——
def test_upload_rejects_dangerous_html_via_api():
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={
            "file": (
                "evil.html",
                b"<html><script>alert(document.cookie)</script></html>",
                "text/html",
            )
        },
        headers=_bearer(),
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "upload_rejected"


def test_upload_accepts_clean_markdown_via_api():
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("note.md", b"# Linear Regression\n\nbody content here", "text/markdown")},
        headers=_bearer(),
    )
    # pg/qdrant 不可用 → 隔离放行后进入 ingest，degraded 200
    assert resp.status_code == 200
