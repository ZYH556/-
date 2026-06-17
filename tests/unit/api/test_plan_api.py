from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser


def _client(monkeypatch) -> TestClient:
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    async def no_pg():
        return None

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr("reflexlearn.api.routes.plan.safe_pg_pool", no_pg)
    return TestClient(app)


def test_plan_item_status_requires_authenticated_user():
    client = TestClient(create_app())

    assert client.patch(
        "/api/plan/items/1/status", json={"status": "done"}
    ).status_code in {401, 403}
    assert client.post(
        "/api/plan/items/insert", json={"after_item_id": 1, "concept": "c"}
    ).status_code in {401, 403}
    assert client.put(
        "/api/plan/items/1/resource", json={"resource_id": "11"}
    ).status_code in {401, 403}


def test_plan_item_status_rejects_unknown_value(monkeypatch):
    client = _client(monkeypatch)

    response = client.patch("/api/plan/items/1/status", json={"status": "finished"})

    assert response.status_code == 422


def test_plan_item_status_degrades_without_pg(monkeypatch):
    client = _client(monkeypatch)

    response = client.patch("/api/plan/items/1/status", json={"status": "done"})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "pg:unavailable" in data["degraded"]


def test_plan_pin_resource_degrades_without_pg(monkeypatch):
    client = _client(monkeypatch)

    response = client.put("/api/plan/items/1/resource", json={"resource_id": "11"})

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "pg:unavailable" in data["degraded"]


def test_plan_insert_degrades_without_pg(monkeypatch):
    client = _client(monkeypatch)

    response = client.post(
        "/api/plan/items/insert", json={"after_item_id": 3, "concept": "损失函数"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "pg:unavailable" in data["degraded"]
