"""W3-B: CSRF 双提交校验（仅 cookie 鉴权请求强制，Bearer 豁免）。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings
from reflexlearn.security.csrf import csrf_validate, generate_csrf_token


@pytest.fixture(autouse=True)
def _no_backends(monkeypatch):
    import reflexlearn.common.db as db
    from reflexlearn.security.rate_limit import reset_login_limiter_for_tests

    async def _none():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _none)
    monkeypatch.setattr(db, "get_redis", _none)
    reset_login_limiter_for_tests()


class _FakeURL:
    def __init__(self, path: str) -> None:
        self.path = path


class FakeRequest:
    def __init__(self, method, path="/api/mistakes", cookies=None, headers=None):
        self.method = method
        self.url = _FakeURL(path)
        self.cookies = cookies or {}
        self.headers = headers or {}


# —— csrf_validate 单元 ——
def test_safe_method_passes():
    assert csrf_validate(FakeRequest("GET")) is True


def test_bearer_without_session_cookie_exempt():
    assert csrf_validate(FakeRequest("POST", cookies={})) is True


def test_login_path_exempt():
    req = FakeRequest("POST", path="/api/auth/login", cookies={"reflexlearn_session": "x"})
    assert csrf_validate(req) is True


def test_cookie_session_without_token_rejected():
    req = FakeRequest("POST", cookies={"reflexlearn_session": "x"})
    assert csrf_validate(req) is False


def test_cookie_session_token_match_passes():
    tok = generate_csrf_token()
    req = FakeRequest(
        "POST",
        cookies={"reflexlearn_session": "x", "reflexlearn_csrf": tok},
        headers={"X-CSRF-Token": tok},
    )
    assert csrf_validate(req) is True


def test_cookie_session_token_mismatch_rejected():
    req = FakeRequest(
        "POST",
        cookies={"reflexlearn_session": "x", "reflexlearn_csrf": "aaa"},
        headers={"X-CSRF-Token": "bbb"},
    )
    assert csrf_validate(req) is False


# —— API 集成 ——
def test_login_sets_csrf_cookie():
    client = TestClient(create_app())
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "reflexlearn-admin"})
    assert resp.status_code == 200
    assert client.cookies.get("reflexlearn_csrf")


def test_cookie_write_without_csrf_rejected():
    client = TestClient(create_app())
    assert client.post(
        "/api/auth/login", json={"username": "admin", "password": "reflexlearn-admin"}
    ).status_code == 200
    resp = client.post(
        "/api/mistakes",
        json={"question": "q", "answer": "a", "expected": "e"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "csrf_failed"


def test_cookie_write_with_csrf_header_passes():
    client = TestClient(create_app())
    assert client.post(
        "/api/auth/login", json={"username": "admin", "password": "reflexlearn-admin"}
    ).status_code == 200
    csrf = client.cookies.get("reflexlearn_csrf")
    assert csrf
    resp = client.post(
        "/api/mistakes",
        json={"question": "q", "answer": "a", "expected": "e"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200


def test_bearer_write_exempt_from_csrf():
    client = TestClient(create_app())
    token = issue_token(CurrentUser(user_id="b1", tenant_id="default", role="student"), Settings())
    resp = client.post(
        "/api/mistakes",
        json={"question": "q", "answer": "a", "expected": "e"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
