import time

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.common.auth import (
    AuthError,
    CurrentUser,
    authenticate_demo_user,
    issue_token,
    validate_auth_runtime,
    verify_token,
)
from reflexlearn.common.config import Settings


def test_security_settings_defaults_are_explicit():
    settings = Settings()
    assert settings.auth_enabled is True
    assert settings.auth_token_ttl_seconds > 0
    assert settings.auth_issuer == "reflexlearn"
    assert "localhost" in settings.cors_allow_origins
    assert settings.max_upload_bytes > 0


def test_demo_user_login_and_token_roundtrip():
    settings = Settings()
    user = authenticate_demo_user("admin", "reflexlearn-admin", settings)
    assert user.user_id == "admin"
    assert user.tenant_id == "default"
    assert user.role == "admin"

    token = issue_token(user, settings)
    verified = verify_token(token, settings)
    assert verified == user


def test_wrong_password_rejected():
    settings = Settings()
    with pytest.raises(AuthError):
        authenticate_demo_user("admin", "bad-password", settings)


def test_tampered_token_rejected():
    settings = Settings()
    token = issue_token(CurrentUser(user_id="u1", tenant_id="t1", role="student"), settings)
    bad = token[:-2] + "xx"
    with pytest.raises(AuthError):
        verify_token(bad, settings)


def test_expired_token_rejected():
    settings = Settings(auth_token_ttl_seconds=-1)
    token = issue_token(CurrentUser(user_id="u1", tenant_id="t1", role="student"), settings)
    time.sleep(0.01)
    with pytest.raises(AuthError):
        verify_token(token, settings)


def test_production_rejects_default_auth_secret():
    settings = Settings(app_env="production")
    user = CurrentUser(user_id="u1", tenant_id="t1", role="student")
    with pytest.raises(AuthError):
        issue_token(user, settings)


def test_production_rejects_auth_disabled():
    settings = Settings(
        app_env="production",
        auth_enabled=False,
        auth_secret_key="x" * 48,
        auth_demo_password="changed-password",
    )
    with pytest.raises(AuthError):
        validate_auth_runtime(settings)


def test_production_rejects_default_demo_password():
    settings = Settings(
        app_env="production",
        auth_secret_key="x" * 48,
        auth_demo_password="reflexlearn-admin",
    )
    with pytest.raises(AuthError):
        validate_auth_runtime(settings)


def test_development_allows_demo_password_for_local_smoke():
    settings = Settings(app_env="development")
    validate_auth_runtime(settings)


def _login_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "reflexlearn-admin"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_and_me_route():
    client = TestClient(create_app())
    headers = _login_headers(client)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user_id"] == "admin"
    assert me.json()["tenant_id"] == "default"
    assert me.json()["role"] == "admin"


def test_me_requires_auth():
    client = TestClient(create_app())
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication_required"


def test_login_rejects_bad_password():
    client = TestClient(create_app())
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert resp.status_code == 401


def test_chat_requires_auth():
    client = TestClient(create_app())
    resp = client.post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 401


def test_knowledge_upload_requires_auth():
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 401


def test_video_submit_requires_auth():
    client = TestClient(create_app())
    resp = client.post("/api/video/jobs", json={"storyboard": "scene"})
    assert resp.status_code == 401


def test_cors_allows_configured_localhost_origin():
    client = TestClient(create_app())
    resp = client.options(
        "/api/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_rejects_unconfigured_origin():
    client = TestClient(create_app())
    resp = client.options(
        "/api/auth/me",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") is None


def test_upload_rejects_unsupported_extension(monkeypatch):
    import reflexlearn.common.db as db

    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("shell.exe", b"MZ\x00\x00", "application/octet-stream")},
        headers=_login_headers(client),
    )
    assert resp.status_code == 415
    assert resp.json()["detail"] == "unsupported_file_type"


def test_upload_rejects_mime_mismatch(monkeypatch):
    import reflexlearn.common.db as db

    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("note.md", b"%PDF- fake", "application/pdf")},
        headers=_login_headers(client),
    )
    assert resp.status_code == 415
    assert resp.json()["detail"] == "file_content_mismatch"


def test_upload_rejects_bad_visibility(monkeypatch):
    import reflexlearn.common.db as db

    async def _no_pg():
        return None

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    client = TestClient(create_app())
    resp = client.post(
        "/api/knowledge/upload",
        files={"file": ("note.md", b"# T\n\nbody", "text/markdown")},
        data={"visibility": "world"},
        headers=_login_headers(client),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid_visibility"
