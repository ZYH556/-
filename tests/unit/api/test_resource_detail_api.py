from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.api.routes.workspace import (
    get_asset_store,
    reset_asset_store_for_tests,
)
from reflexlearn.common.auth import CurrentUser


def _client(monkeypatch, user_id: str = "student-a") -> TestClient:
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id=user_id, tenant_id="demo", role="student")

    async def no_pg():
        return None

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr("reflexlearn.api.routes.workspace.safe_pg_pool", no_pg)
    return TestClient(app)


def _seed_resource(owner: str = "student-a") -> None:
    get_asset_store().seed_memory(
        resources=[
            {
                "resource_id": "res-1",
                "user_id": owner,
                "tenant_id": "demo",
                "type": "doc",
                "title": "损失函数讲解",
                "content_preview": "围绕损失函数的讲解文档。",
                "visibility": "private",
            }
        ]
    )


def test_resource_detail_requires_authenticated_user():
    client = TestClient(create_app())

    assert client.get("/api/resources/res-1/detail").status_code in {401, 403}
    assert client.patch(
        "/api/resources/res-1/status", json={"status": "done"}
    ).status_code in {401, 403}


def test_resource_detail_404_when_missing(monkeypatch):
    reset_asset_store_for_tests()
    client = _client(monkeypatch)

    assert client.get("/api/resources/no-such/detail").status_code == 404


def test_resource_detail_forbidden_for_other_user(monkeypatch):
    reset_asset_store_for_tests()
    _seed_resource(owner="owner-b")
    client = _client(monkeypatch, user_id="student-a")

    assert client.get("/api/resources/res-1/detail").status_code == 403
    assert client.patch(
        "/api/resources/res-1/status", json={"status": "done"}
    ).status_code == 403


def test_resource_detail_degrades_without_pg(monkeypatch):
    reset_asset_store_for_tests()
    _seed_resource()
    client = _client(monkeypatch)

    response = client.get("/api/resources/res-1/detail")

    assert response.status_code == 200
    data = response.json()
    assert data["resource"]["title"] == "损失函数讲解"
    assert data["study_status"] == "unread"
    assert "pg:unavailable" in data["degraded"]


def test_status_roundtrip_in_memory_fallback(monkeypatch):
    reset_asset_store_for_tests()
    _seed_resource()
    client = _client(monkeypatch)

    updated = client.patch("/api/resources/res-1/status", json={"status": "done"})
    assert updated.status_code == 200
    assert updated.json()["study_status"] == "done"

    detail = client.get("/api/resources/res-1/detail").json()
    assert detail["study_status"] == "done"
    assert detail["status_updated_at"] is not None


def test_status_rejects_unknown_value(monkeypatch):
    reset_asset_store_for_tests()
    _seed_resource()
    client = _client(monkeypatch)

    response = client.patch("/api/resources/res-1/status", json={"status": "finished"})

    assert response.status_code == 422
