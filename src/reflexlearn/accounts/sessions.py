"""HttpOnly Cookie 会话：登录设 cookie、登出清 cookie、读取 cookie。

cookie 值即现有 HMAC 会话 token（common.auth.issue_token），由 deps 用
verify_token 校验。生产环境 Secure=True。
"""

from __future__ import annotations

from fastapi import Request, Response

from reflexlearn.common.config import Settings, get_settings


def _cfg(settings: Settings | None) -> Settings:
    return settings or get_settings()


def _is_secure(settings: Settings) -> bool:
    return settings.app_env.lower() == "production"


def set_session_cookie(response: Response, token: str, settings: Settings | None = None) -> None:
    cfg = _cfg(settings)
    response.set_cookie(
        key=cfg.session_cookie_name,
        value=token,
        max_age=cfg.auth_token_ttl_seconds,
        httponly=True,
        secure=_is_secure(cfg),
        samesite=cfg.session_cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings | None = None) -> None:
    cfg = _cfg(settings)
    response.delete_cookie(
        key=cfg.session_cookie_name,
        path="/",
        samesite=cfg.session_cookie_samesite,
    )


def read_session_cookie(request: Request, settings: Settings | None = None) -> str | None:
    cfg = _cfg(settings)
    return request.cookies.get(cfg.session_cookie_name)
