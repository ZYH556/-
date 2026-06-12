"""CSRF 双提交 cookie 防护。

设计：仅对"用 HttpOnly session cookie 鉴权"的写请求强制 CSRF；纯 Bearer
请求（无 session cookie，攻击者无法注入 Authorization）天然免疫，豁免校验，
保证脚本/API 调用不受影响。GET/HEAD/OPTIONS 与 /auth/login、/auth/register、/auth/social、/auth/logout 豁免。
"""

from __future__ import annotations

import hmac
import secrets

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from reflexlearn.common.config import Settings, get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_HEADER = "X-CSRF-Token"


def _cfg(settings: Settings | None) -> Settings:
    return settings or get_settings()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str, settings: Settings | None = None) -> None:
    cfg = _cfg(settings)
    response.set_cookie(
        key=cfg.csrf_cookie_name,
        value=token,
        max_age=cfg.auth_token_ttl_seconds,
        httponly=False,  # double-submit：前端需读取放入 X-CSRF-Token 头
        secure=cfg.app_env.lower() == "production",
        samesite=cfg.session_cookie_samesite,
        path="/",
    )


def clear_csrf_cookie(response, settings: Settings | None = None) -> None:
    cfg = _cfg(settings)
    response.delete_cookie(
        key=cfg.csrf_cookie_name,
        path="/",
        samesite=cfg.session_cookie_samesite,
    )


def _is_exempt_path(path: str) -> bool:
    return (
        path.endswith("/auth/login")
        or path.endswith("/auth/register")
        or path.endswith("/auth/social")
        or path.endswith("/auth/logout")
    )


def csrf_validate(request: Request, settings: Settings | None = None) -> bool:
    """True 表示通过或无需校验；False 表示 CSRF 校验失败。"""
    cfg = _cfg(settings)
    if request.method in SAFE_METHODS:
        return True
    if _is_exempt_path(request.url.path):
        return True
    # 带 Authorization 头的请求（Bearer）天然抗 CSRF——跨站攻击无法注入自定义头，
    # 故豁免；脚本/API/开发 Bearer 不受影响。
    if request.headers.get("Authorization"):
        return True
    # 仅靠 session cookie 自动鉴权的写请求才强制 CSRF。
    if not request.cookies.get(cfg.session_cookie_name):
        return True
    header = request.headers.get(CSRF_HEADER)
    cookie = request.cookies.get(cfg.csrf_cookie_name)
    if not header or not cookie:
        return False
    return hmac.compare_digest(header, cookie)


class CSRFMiddleware:
    """纯 ASGI 中间件：仅在请求阶段校验 CSRF，不包装下游 response，
    避免破坏 /chat 的 SSE 流式输出。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not csrf_validate(Request(scope)):
            response = JSONResponse(status_code=403, content={"detail": "csrf_failed"})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
