from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser


def test_resource_discovery_requires_authenticated_user():
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/api/resources/discover",
        json={"goal": "线性回归", "weak_points": ["损失函数"]},
    )

    assert response.status_code in {401, 403}


def test_resource_discovery_returns_candidates_for_authenticated_user():
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    app.dependency_overrides[get_current_user] = fake_user
    client = TestClient(app)

    response = client.post(
        "/api/resources/discover",
        json={
            "goal": "掌握线性回归与梯度下降",
            "weak_points": ["损失函数", "梯度方向"],
            "providers": ["bilibili", "official_doc"],
            "limit": 4,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"]["goal"] == "掌握线性回归与梯度下降"
    assert data["query"]["weak_points"] == ["损失函数", "梯度方向"]
    assert data["items"]
    assert all(item["usage_mode"] == "metadata_only" for item in data["items"])
    assert all(item["source_policy"] == "embed_or_redirect_only" for item in data["items"])
    assert {item["provider"] for item in data["items"]} >= {"Bilibili", "scikit-learn"}
