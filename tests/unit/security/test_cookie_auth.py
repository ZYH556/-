"""W3-A: HttpOnly Cookie 会话登录/登出/读取。

PG 用 autouse mock 置 None，走 development demo fallback，确保不真连 PG。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings


@pytest.fixture(autouse=True)
def _no_pg(monkeypatch):
    import reflexlearn.common.db as db
    from reflexlearn.security.rate_limit import reset_login_limiter_for_tests

    async def _none():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _none)
    monkeypatch.setattr(db, "get_redis", _none)
    reset_login_limiter_for_tests()


def _login(client: TestClient):
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "reflexlearn-admin"},
    )


def test_login_sets_httponly_session_cookie():
    client = TestClient(create_app())
    resp = _login(client)
    assert resp.status_code == 200
    set_cookie = resp.headers.get("set-cookie", "")
    assert "reflexlearn_session=" in set_cookie
    assert "httponly" in set_cookie.lower()
    body = resp.json()
    assert body["user"]["user_id"] == "admin"
    assert body["user"]["role"] == "admin"


def test_me_reads_session_cookie_without_bearer():
    client = TestClient(create_app())
    assert _login(client).status_code == 200
    # TestClient 自动携带登录设置的 cookie；不带 Authorization 头
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user_id"] == "admin"


def test_logout_clears_cookie_then_me_unauthorized():
    client = TestClient(create_app())
    assert _login(client).status_code == 200
    out = client.post("/api/auth/logout")
    assert out.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 401
    assert me.json()["detail"] == "authentication_required"


def test_me_without_credentials_is_unauthorized():
    client = TestClient(create_app())
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_bearer_still_authenticates_for_dev_scripts():
    client = TestClient(create_app())
    token = issue_token(
        CurrentUser(user_id="script-1", tenant_id="default", role="student"),
        Settings(),
    )
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user_id"] == "script-1"


def test_login_still_exposes_token_in_development():
    """开发环境保留 access_token 供脚本烟测；生产应为 None（见 store/route 逻辑）。"""
    client = TestClient(create_app())
    body = _login(client).json()
    assert body.get("access_token")
