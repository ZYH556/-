from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping
from typing import Literal, cast

from pydantic import BaseModel, ValidationError

from reflexlearn.common.config import Settings, get_settings

Role = Literal["student", "teacher", "admin", "evaluator"]


class AuthError(Exception):
    pass


class CurrentUser(BaseModel):
    user_id: str
    tenant_id: str
    role: Role = "student"


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: Role
    iat: int
    exp: int
    iss: str
    aud: str
    jti: str


class AuthToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: CurrentUser


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _json_dumps(data: Mapping[str, object]) -> bytes:
    return json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _settings(settings: Settings | None) -> Settings:
    return settings or get_settings()


def _assert_secret(settings: Settings) -> None:
    default = "dev-only-change-me-reflexlearn-auth-secret"
    if settings.app_env.lower() == "production" and settings.auth_secret_key == default:
        raise AuthError("auth secret must be changed in production")
    if len(settings.auth_secret_key) < 32:
        raise AuthError("auth secret is too short")


def _role(value: str) -> Role:
    if value in {"student", "teacher", "admin", "evaluator"}:
        return cast(Role, value)
    raise AuthError("invalid configured role")


def authenticate_demo_user(
    username: str,
    password: str,
    settings: Settings | None = None,
) -> CurrentUser:
    cfg = _settings(settings)
    user_ok = hmac.compare_digest(username, cfg.auth_demo_username)
    pass_ok = hmac.compare_digest(password, cfg.auth_demo_password)
    if not (user_ok and pass_ok):
        raise AuthError("invalid credentials")
    return CurrentUser(
        user_id=cfg.auth_demo_username,
        tenant_id=cfg.auth_demo_tenant_id,
        role=_role(cfg.auth_demo_role),
    )


def validate_auth_runtime(settings: Settings | None = None) -> None:
    cfg = _settings(settings)
    if cfg.app_env.lower() != "production":
        return
    if not cfg.auth_enabled:
        raise AuthError("auth cannot be disabled in production")
    _assert_secret(cfg)
    if cfg.auth_demo_password == "reflexlearn-admin":
        raise AuthError("default demo password cannot be used in production")


def issue_token(user: CurrentUser, settings: Settings | None = None) -> str:
    cfg = _settings(settings)
    _assert_secret(cfg)
    now = int(time.time())
    payload = TokenPayload(
        sub=user.user_id,
        tenant_id=user.tenant_id,
        role=user.role,
        iat=now,
        exp=now + cfg.auth_token_ttl_seconds,
        iss=cfg.auth_issuer,
        aud=cfg.auth_audience,
        jti=secrets.token_urlsafe(12),
    )
    header = {"alg": "HS256", "typ": "RLT"}
    header_part = _b64e(_json_dumps(header))
    payload_part = _b64e(payload.model_dump_json().encode("utf-8"))
    signing_input = f"{header_part}.{payload_part}"
    sig = hmac.new(
        cfg.auth_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64e(sig)}"


def verify_token(token: str, settings: Settings | None = None) -> CurrentUser:
    cfg = _settings(settings)
    _assert_secret(cfg)
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as exc:
        raise AuthError("malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}"
    expected = hmac.new(
        cfg.auth_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        provided = _b64d(sig_b64)
    except ValueError as exc:
        raise AuthError("invalid token signature") from exc
    if not hmac.compare_digest(expected, provided):
        raise AuthError("invalid token signature")

    try:
        header_raw = json.loads(_b64d(header_b64))
        payload = TokenPayload.model_validate_json(_b64d(payload_b64))
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise AuthError("invalid token payload") from exc
    if not isinstance(header_raw, dict):
        raise AuthError("invalid token header")
    if header_raw.get("alg") != "HS256" or header_raw.get("typ") != "RLT":
        raise AuthError("invalid token header")
    now = int(time.time())
    if payload.exp <= now:
        raise AuthError("token expired")
    if payload.iss != cfg.auth_issuer or payload.aud != cfg.auth_audience:
        raise AuthError("token audience mismatch")
    return CurrentUser(user_id=payload.sub, tenant_id=payload.tenant_id, role=payload.role)
