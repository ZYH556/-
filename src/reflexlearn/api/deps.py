from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from reflexlearn.accounts.sessions import read_session_cookie
from reflexlearn.common.auth import AuthError, CurrentUser, validate_auth_runtime, verify_token
from reflexlearn.common.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


async def get_current_settings(settings: Settings = Depends(get_settings)):
    return settings


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    settings = get_settings()
    try:
        validate_auth_runtime(settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_misconfigured",
        ) from exc
    if not settings.auth_enabled:
        return CurrentUser(
            user_id=settings.auth_demo_username,
            tenant_id=settings.auth_demo_tenant_id,
            role="admin",
        )
    # 优先 HttpOnly cookie 会话（W3-A 生产路径）
    cookie_token = read_session_cookie(request, settings)
    if cookie_token:
        try:
            return verify_token(cookie_token, settings)
        except AuthError:
            pass  # cookie 失效则回退 Bearer（开发/脚本烟测）
    # 兼容 Bearer（development / 脚本）
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            return verify_token(credentials.credentials, settings)
        except AuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="authentication_required",
            ) from exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="authentication_required",
    )


def require_roles(*roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    async def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission_denied",
            )
        return user

    return _dependency
