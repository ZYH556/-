from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import (
    AuthError,
    AuthToken,
    CurrentUser,
    authenticate_demo_user,
    issue_token,
    validate_auth_runtime,
)
from reflexlearn.common.config import get_settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(body: LoginRequest) -> AuthToken:
    settings = get_settings()
    try:
        validate_auth_runtime(settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_misconfigured",
        ) from exc
    try:
        user = authenticate_demo_user(body.username, body.password, settings)
        token = issue_token(user, settings)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
        ) from exc
    return AuthToken(
        access_token=token,
        expires_in=settings.auth_token_ttl_seconds,
        user=user,
    )


@router.get("/auth/me")
async def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
