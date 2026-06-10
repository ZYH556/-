"""W3-D: HMAC 签名 URL（短 TTL，绑定 object/tenant/user/过期）。"""

from __future__ import annotations

from reflexlearn.common.config import Settings
from reflexlearn.security.signed_url import sign_object, verify_object

_S = Settings(signed_url_ttl_s=300)


def test_sign_and_verify_roundtrip():
    signed = sign_object(object_id="o1", tenant_id="t1", user_id="u1", settings=_S, now=1000.0)
    assert signed.expires == 1300
    assert verify_object(
        object_id="o1",
        tenant_id="t1",
        user_id="u1",
        expires=signed.expires,
        signature=signed.signature,
        settings=_S,
        now=1000.0,
    )


def test_expired_signature_rejected():
    signed = sign_object(object_id="o1", tenant_id="t1", user_id="u1", settings=_S, now=1000.0)
    assert not verify_object(
        object_id="o1",
        tenant_id="t1",
        user_id="u1",
        expires=signed.expires,
        signature=signed.signature,
        settings=_S,
        now=signed.expires + 1,
    )


def test_tampered_signature_rejected():
    signed = sign_object(object_id="o1", tenant_id="t1", user_id="u1", settings=_S, now=1000.0)
    assert not verify_object(
        object_id="o1",
        tenant_id="t1",
        user_id="u1",
        expires=signed.expires,
        signature="deadbeef",
        settings=_S,
        now=1000.0,
    )


def test_cross_user_rejected():
    signed = sign_object(object_id="o1", tenant_id="t1", user_id="u1", settings=_S, now=1000.0)
    assert not verify_object(
        object_id="o1",
        tenant_id="t1",
        user_id="intruder",
        expires=signed.expires,
        signature=signed.signature,
        settings=_S,
        now=1000.0,
    )


def test_cross_object_rejected():
    signed = sign_object(object_id="o1", tenant_id="t1", user_id="u1", settings=_S, now=1000.0)
    assert not verify_object(
        object_id="other-object",
        tenant_id="t1",
        user_id="u1",
        expires=signed.expires,
        signature=signed.signature,
        settings=_S,
        now=1000.0,
    )
