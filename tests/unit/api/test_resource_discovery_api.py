from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser
from reflexlearn.learning.mdn_search import MdnDoc


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


def _web_client(monkeypatch, mdn_return):
    """构造已登录 client，并把 MDN search_docs 固定为给定返回（覆盖 conftest 守卫）。"""
    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    async def fake_search_docs(self, keyword, *, limit=2, locale="zh-CN"):
        return mdn_return

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr(
        "reflexlearn.learning.mdn_search.MdnSearchClient.search_docs", fake_search_docs
    )
    return TestClient(app)


def _post_discover(client, goal, weak_points):
    return client.post(
        "/api/resources/discover",
        json={"goal": goal, "weak_points": weak_points, "providers": ["official_doc"], "limit": 6},
    )


def test_discover_web_topic_merges_real_mdn(monkeypatch):
    docs = [
        MdnDoc(
            title="Promise",
            url="https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Promise",
            summary="异步计算",
            score=50,
        )
    ]
    client = _web_client(monkeypatch, docs)

    data = _post_discover(client, "JavaScript 异步编程", ["Promise"]).json()

    assert "mdn:live" in data["degraded"]
    assert any(item["provider"] == "MDN" for item in data["items"])


def test_discover_web_topic_mdn_none_falls_back(monkeypatch):
    client = _web_client(monkeypatch, None)

    data = _post_discover(client, "JavaScript 异步编程", ["Promise"]).json()

    assert "mdn:fallback_static" in data["degraded"]
    assert "mdn:live" not in data["degraded"]


def test_discover_non_web_topic_skips_mdn(monkeypatch):
    calls = {"n": 0}

    async def spy_search_docs(self, keyword, *, limit=2, locale="zh-CN"):
        calls["n"] += 1
        return None

    app = create_app()

    async def fake_user():
        return CurrentUser(user_id="student-a", tenant_id="demo", role="student")

    app.dependency_overrides[get_current_user] = fake_user
    monkeypatch.setattr(
        "reflexlearn.learning.mdn_search.MdnSearchClient.search_docs", spy_search_docs
    )
    client = TestClient(app)

    data = _post_discover(client, "线性回归入门", ["数学推导"]).json()

    assert calls["n"] == 0  # 非 Web 目标：门控跳过，不外呼 MDN
    assert "mdn:live" not in data["degraded"]
    assert "mdn:fallback_static" not in data["degraded"]
