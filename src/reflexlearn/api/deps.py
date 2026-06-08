from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from reflexlearn.common.auth import AuthError, CurrentUser, validate_auth_runtime, verify_token
from reflexlearn.common.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


async def get_current_settings(settings: Settings = Depends(get_settings)):
    return settings


async def get_current_user(
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
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        )
    try:
        return verify_token(credentials.credentials, settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        ) from exc


def require_roles(*roles: str) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    async def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission_denied",
            )
        return user

    return _dependency
