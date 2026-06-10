from fastapi.testclient import TestClient

import reflexlearn.api.routes.workspace as route
import reflexlearn.common.db as db
from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings
from reflexlearn.learning.assets import LearningAssetStore


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def _client_with_memory(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    store = LearningAssetStore()
    store.seed_memory(
        spaces=[
            {
                "space_id": "s1",
                "user_id": "u1",
                "tenant_id": "default",
                "title": "线性回归空间",
            },
            {
                "space_id": "s2",
                "user_id": "u2",
                "tenant_id": "default",
                "title": "他人空间",
            },
        ],
        resources=[
            {
                "resource_id": "r1",
                "user_id": "u1",
                "tenant_id": "default",
                "type": "doc",
                "title": "个人讲解",
            },
            {
                "resource_id": "r2",
                "user_id": "u2",
                "tenant_id": "default",
                "type": "quiz",
                "title": "他人练习",
            },
        ],
        documents=[
            {
                "doc_id": "d1",
                "user_id": "u1",
                "tenant_id": "default",
                "visibility": "private",
                "title": "个人资料",
            },
            {
                "doc_id": "d2",
                "user_id": "u2",
                "tenant_id": "default",
                "visibility": "private",
                "title": "他人资料",
            },
            {
                "doc_id": "d3",
                "user_id": "u2",
                "tenant_id": "default",
                "visibility": "public",
                "title": "公共资料",
            },
        ],
    )
    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.set_asset_store_for_tests(store)
    return TestClient(create_app())


def test_workspace_lists_filter_by_current_user(monkeypatch):
    client = _client_with_memory(monkeypatch)

    spaces = client.get("/api/spaces", headers=_headers("u1")).json()
    resources = client.get("/api/resources", headers=_headers("u1")).json()
    docs = client.get("/api/knowledge/documents", headers=_headers("u1")).json()

    assert [item["space_id"] for item in spaces["items"]] == ["s1"]
    assert [item["resource_id"] for item in resources["items"]] == ["r1"]
    assert [item["doc_id"] for item in docs["items"]] == ["d1", "d3"]
    route.reset_asset_store_for_tests()


def test_workspace_detail_cross_user_returns_403(monkeypatch):
    client = _client_with_memory(monkeypatch)

    assert client.get("/api/spaces/s1", headers=_headers("u1")).status_code == 200
    assert client.get("/api/spaces/s1", headers=_headers("u2")).status_code == 403
    assert client.get("/api/resources/r1", headers=_headers("u2")).status_code == 403
    assert client.get("/api/knowledge/documents/d1", headers=_headers("u2")).status_code == 403
    assert client.get("/api/knowledge/documents/d3", headers=_headers("u1")).status_code == 200
    route.reset_asset_store_for_tests()
