from fastapi.testclient import TestClient

import reflexlearn.api.routes.mistakes as route
import reflexlearn.common.db as db
from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def test_mistake_create_list_review_degrades_without_pg(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.reset_mistake_store_for_tests()
    client = TestClient(create_app())

    created = client.post(
        "/api/mistakes",
        json={
            "question": "为什么过拟合模型泛化差？",
            "answer": "训练集太少",
            "expected": "模型复杂度过高，需要正则化和验证集约束。",
            "concept": "过拟合",
        },
        headers=_headers("u1"),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["mistake_id"]
    assert "pg:unavailable" in body["degraded"]

    listing = client.get("/api/mistakes", headers=_headers("u1"))
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1

    review = client.post(
        f"/api/mistakes/{body['mistake_id']}/review",
        headers=_headers("u1"),
    )
    assert review.status_code == 200
    assert review.json()["mistake_id"] == body["mistake_id"]
    assert review.json()["review_plan"]
    route.reset_mistake_store_for_tests()


def test_mistake_cross_user_returns_403(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.reset_mistake_store_for_tests()
    client = TestClient(create_app())

    created = client.post(
        "/api/mistakes",
        json={"question": "Q", "answer": "A", "expected": "B"},
        headers=_headers("u1"),
    )
    assert created.status_code == 200
    mistake_id = created.json()["mistake_id"]

    detail = client.get(f"/api/mistakes/{mistake_id}", headers=_headers("u2"))
    assert detail.status_code == 403
    assert detail.json()["detail"] == "permission_denied"
    route.reset_mistake_store_for_tests()


def test_mistake_flywheel_end_to_end(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.reset_mistake_store_for_tests()
    client = TestClient(create_app())

    created = client.post(
        "/api/mistakes",
        json={
            "question": "用 Python 写线性回归梯度下降，为什么损失没有下降？",
            "answer": "直接用梯度加到参数上。",
            "expected": "应沿负梯度方向更新，并检查学习率和梯度公式。",
            "concept": "梯度下降",
        },
        headers=_headers("u1"),
    )
    assert created.status_code == 200
    mistake_id = created.json()["mistake_id"]

    reflected = client.post(f"/api/mistakes/{mistake_id}/reflect", headers=_headers("u1"))
    planned = client.post(f"/api/mistakes/{mistake_id}/plan", headers=_headers("u1"))
    resources = client.post(f"/api/mistakes/{mistake_id}/resources", headers=_headers("u1"))
    reviewed = client.patch(
        f"/api/mistakes/{mistake_id}/review",
        json={"review_status": "reviewed"},
        headers=_headers("u1"),
    )

    assert reflected.status_code == 200
    assert reflected.json()["category"] in {
        "概念不清",
        "步骤遗漏",
        "公式/代码错误",
        "审题偏差",
        "记忆遗忘",
    }
    assert planned.status_code == 200
    assert 3 <= len(planned.json()["steps"]) <= 5
    assert resources.status_code == 200
    resource_types = {item["type"] for item in resources.json()["resources"]}
    assert {"doc", "quiz"}.issubset(resource_types)
    assert all(item["mistake_id"] == mistake_id for item in resources.json()["resources"])
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    route.reset_mistake_store_for_tests()


def test_mistake_flywheel_acl_and_not_found(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.reset_mistake_store_for_tests()
    client = TestClient(create_app())
    created = client.post(
        "/api/mistakes",
        json={"question": "Q", "answer": "A", "expected": "B", "concept": "C"},
        headers=_headers("u1"),
    )
    mistake_id = created.json()["mistake_id"]

    for method, path in [
        ("post", f"/api/mistakes/{mistake_id}/reflect"),
        ("post", f"/api/mistakes/{mistake_id}/plan"),
        ("post", f"/api/mistakes/{mistake_id}/resources"),
        ("patch", f"/api/mistakes/{mistake_id}/review"),
    ]:
        resp = getattr(client, method)(path, json={"review_status": "reviewed"}, headers=_headers("u2"))
        assert resp.status_code == 403
        assert resp.json()["detail"] == "permission_denied"

    missing = client.post("/api/mistakes/not-exists/reflect", headers=_headers("u1"))
    assert missing.status_code == 404
    assert missing.json()["error"] == "mistake_not_found"
    route.reset_mistake_store_for_tests()
