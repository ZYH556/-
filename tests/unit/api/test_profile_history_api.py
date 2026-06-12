from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser


def test_profile_history_requires_authenticated_user():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/profile/history")

    assert response.status_code in {401, 403}


def test_profile_history_degrades_when_pg_is_unavailable(monkeypatch):
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    async def no_pg():
        return None

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr("reflexlearn.api.routes.profile.safe_pg_pool", no_pg)
    client = TestClient(app)

    response = client.get("/api/profile/history")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert "pg:unavailable" in data["degraded"]
