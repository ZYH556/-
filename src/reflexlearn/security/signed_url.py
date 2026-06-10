"""W3-D 签名 URL：HMAC 绑定 object_id/tenant/user/过期时间，短 TTL，不暴露原始公网 URL。"""

from __future__ import annotations

import hashlib
import hmac
import time

from pydantic import BaseModel

from reflexlearn.common.config import Settings, get_settings


class SignedUrl(BaseModel):
    object_id: str
    tenant_id: str
    user_id: str
    expires: int
    signature: str


def _cfg(settings: Settings | None) -> Settings:
    return settings or get_settings()


def _payload(object_id: str, tenant_id: str, user_id: str, expires: int) -> str:
    return f"{object_id}:{tenant_id}:{user_id}:{expires}"


def _sign(payload: str, cfg: Settings) -> str:
    return hmac.new(
        cfg.auth_secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def sign_object(
    *,
    object_id: str,
    tenant_id: str,
    user_id: str,
    settings: Settings | None = None,
    now: float | None = None,
) -> SignedUrl:
    cfg = _cfg(settings)
    base = now if now is not None else time.time()
    expires = int(base + cfg.signed_url_ttl_s)
    signature = _sign(_payload(object_id, tenant_id, user_id, expires), cfg)
    return SignedUrl(
        object_id=object_id,
        tenant_id=tenant_id,
        user_id=user_id,
        expires=expires,
        signature=signature,
    )


def verify_object(
    *,
    object_id: str,
    tenant_id: str,
    user_id: str,
    expires: int,
    signature: str,
    settings: Settings | None = None,
    now: float | None = None,
) -> bool:
    cfg = _cfg(settings)
    current = int(now if now is not None else time.time())
    if int(expires) < current:
        return False
    expected = _sign(_payload(object_id, tenant_id, user_id, int(expires)), cfg)
    return hmac.compare_digest(expected, str(signature))
