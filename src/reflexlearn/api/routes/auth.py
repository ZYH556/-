from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

from reflexlearn.accounts.sessions import clear_session_cookie, set_session_cookie
from reflexlearn.accounts.store import AccountStore
from reflexlearn.api.deps import get_current_user
from reflexlearn.api.service_deps import safe_pg_pool, safe_redis
from reflexlearn.common.auth import (
    AuthError,
    CurrentUser,
    issue_token,
    validate_auth_runtime,
)
from reflexlearn.common.config import get_settings
from reflexlearn.security.audit import AuditEvent, AuditLog
from reflexlearn.security.csrf import clear_csrf_cookie, generate_csrf_token, set_csrf_cookie
from reflexlearn.security.rate_limit import get_login_limiter

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user: CurrentUser
    token_type: str = "bearer"
    expires_in: int
    # 开发/脚本烟测保留 access_token；生产返回 None，凭证只走 HttpOnly cookie。
    access_token: str | None = None


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.post("/auth/login")
async def login(body: LoginRequest, request: Request, response: Response) -> LoginResponse:
    settings = get_settings()
    try:
        validate_auth_runtime(settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_misconfigured",
        ) from exc

    ip = _client_ip(request)
    pool = await safe_pg_pool()
    audit = AuditLog(pg_pool=pool)

    if settings.enable_login_rate_limit:
        redis = await safe_redis()
        rate_key = f"{settings.auth_demo_tenant_id}/{ip}/{body.username}"
        allowed = await get_login_limiter(settings).hit(rate_key, redis=redis)
        if not allowed:
            await audit.record(
                AuditEvent(event_type="auth.login", user_id=body.username, ip=ip, status="rate_limited")
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too_many_attempts",
            )

    store = AccountStore(pg_pool=pool, settings=settings)
    try:
        account = await store.authenticate(body.username, body.password)
    except AuthError as exc:
        await audit.record(
            AuditEvent(event_type="auth.login", user_id=body.username, ip=ip, status="failed")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        ) from exc

    user = CurrentUser(
        user_id=account.user_id,
        tenant_id=account.tenant_id,
        role=account.role,
    )
    token = issue_token(user, settings)
    set_session_cookie(response, token, settings)
    set_csrf_cookie(response, generate_csrf_token(), settings)
    await audit.record(
        AuditEvent(
            event_type="auth.login",
            user_id=user.user_id,
            tenant_id=user.tenant_id,
            ip=ip,
            status="ok",
        )
    )
    expose_token = None if settings.app_env.lower() == "production" else token
    return LoginResponse(
        user=user,
        expires_in=settings.auth_token_ttl_seconds,
        access_token=expose_token,
    )


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> dict[str, str]:
    settings = get_settings()
    clear_session_cookie(response, settings)
    clear_csrf_cookie(response, settings)
    pool = await safe_pg_pool()
    await AuditLog(pg_pool=pool).record(
        AuditEvent(event_type="auth.logout", ip=_client_ip(request), status="ok")
    )
    return {"status": "ok"}


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
