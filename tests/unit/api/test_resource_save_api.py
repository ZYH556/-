from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.api.routes.workspace import reset_asset_store_for_tests
from reflexlearn.common.auth import CurrentUser


PAYLOAD = {
    "candidate_id": "candidate-bilibili-test",
    "type": "external_video",
    "title": "损失函数 可视化讲解",
    "provider": "Bilibili",
    "source_label": "B 站视频",
    "href": "https://search.bilibili.com/all?keyword=loss",
    "usage_mode": "metadata_only",
    "source_policy": "embed_or_redirect_only",
    "estimated_minutes": 16,
    "reason": "先补感性理解",
    "concept": "损失函数",
}


def _client_with_user(monkeypatch) -> TestClient:
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    async def no_pg():
        return None

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr("reflexlearn.api.routes.workspace.safe_pg_pool", no_pg)
    return TestClient(app)


def test_save_resource_requires_authenticated_user():
    app = create_app()
    client = TestClient(app)

    response = client.post("/api/resources/save", json=PAYLOAD)

    assert response.status_code in {401, 403}


def test_save_resource_persists_candidate(monkeypatch):
    reset_asset_store_for_tests()
    client = _client_with_user(monkeypatch)

    response = client.post("/api/resources/save", json=PAYLOAD)

    assert response.status_code == 200
    data = response.json()
    assert data["saved"] is True
    assert data["duplicate"] is False
    assert data["resource_id"] == "candidate-bilibili-test"
    assert "pg:unavailable" in data["degraded"]

    listing = client.get("/api/resources").json()
    titles = [item["title"] for item in listing["items"]]
    assert "损失函数 可视化讲解" in titles


def test_save_resource_is_idempotent_per_candidate(monkeypatch):
    reset_asset_store_for_tests()
    client = _client_with_user(monkeypatch)

    first = client.post("/api/resources/save", json=PAYLOAD)
    second = client.post("/api/resources/save", json=PAYLOAD)

    assert first.json()["duplicate"] is False
    assert second.json()["duplicate"] is True

    listing = client.get("/api/resources").json()
    assert len([i for i in listing["items"] if i["title"] == PAYLOAD["title"]]) == 1
