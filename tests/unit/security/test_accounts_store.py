"""W3-A: DB 用户账户存储与密码哈希。

passwords 为纯函数（无外部依赖）；AccountStore 走依赖注入的 pg_pool，
PG 不可用时仅 development 允许 demo fallback，绝不在被测函数内自取 PG。
"""

from __future__ import annotations

import pytest

from reflexlearn.accounts.models import Account
from reflexlearn.accounts.passwords import hash_password, verify_password
from reflexlearn.accounts.store import AccountStore
from reflexlearn.common.auth import AuthError
from reflexlearn.common.config import Settings


# —— 假 PG 连接池（仿 asyncpg.acquire 上下文，绝不真连）——
class _FakeConn:
    def __init__(self, row: dict | None) -> None:
        self._row = row
        self.executed: list[tuple] = []

    async def fetchrow(self, _query: str, *args):
        return self._row

    async def execute(self, query: str, *args):
        self.executed.append((query, args))


class _FakeAcquire:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, *_a) -> bool:
        return False


class FakePgPool:
    def __init__(self, row: dict | None = None) -> None:
        self.conn = _FakeConn(row)

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self.conn)


# —— passwords 纯函数 ——
def test_hash_password_roundtrip():
    encoded = hash_password("s3cret-pw")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("s3cret-pw", encoded) is True
    assert verify_password("wrong-pw", encoded) is False


def test_hash_password_uses_random_salt():
    a = hash_password("same-pw")
    b = hash_password("same-pw")
    assert a != b
    assert verify_password("same-pw", a)
    assert verify_password("same-pw", b)


def test_verify_rejects_malformed_hash():
    assert verify_password("anything", "not-a-valid-encoded-hash") is False
    assert verify_password("anything", "") is False


# —— AccountStore 降级路径 ——
async def test_pg_unavailable_demo_fallback_in_development():
    store = AccountStore(pg_pool=None, settings=Settings(app_env="development"))
    account = await store.authenticate("admin", "reflexlearn-admin")
    assert account.user_id == "admin"
    assert account.role == "admin"
    assert account.tenant_id == "default"


async def test_pg_unavailable_rejects_wrong_demo_password():
    store = AccountStore(pg_pool=None, settings=Settings(app_env="development"))
    with pytest.raises(AuthError):
        await store.authenticate("admin", "wrong-password")


async def test_pg_unavailable_no_demo_fallback_in_production():
    store = AccountStore(
        pg_pool=None,
        settings=Settings(
            app_env="production",
            auth_secret_key="x" * 48,
            auth_demo_password="changed-prod-password",
        ),
    )
    with pytest.raises(AuthError):
        await store.authenticate("admin", "changed-prod-password")


# —— AccountStore PG 路径（注入假 pool）——
async def test_authenticate_via_pg_row():
    encoded = hash_password("pg-pw-123", iterations=1000)
    row = {
        "id": "u1",
        "role": "student",
        "tenant_id": "t-x",
        "password_hash": encoded,
        "password_alg": "pbkdf2_sha256",
        "disabled": False,
    }
    store = AccountStore(pg_pool=FakePgPool(row=row), settings=Settings())
    account = await store.authenticate("u1", "pg-pw-123")
    assert account.user_id == "u1"
    assert account.tenant_id == "t-x"
    assert account.role == "student"
    with pytest.raises(AuthError):
        await store.authenticate("u1", "bad-pw")


async def test_disabled_account_rejected():
    encoded = hash_password("pw", iterations=1000)
    row = {
        "id": "u2",
        "role": "student",
        "tenant_id": "default",
        "password_hash": encoded,
        "password_alg": "pbkdf2_sha256",
        "disabled": True,
    }
    store = AccountStore(pg_pool=FakePgPool(row=row), settings=Settings())
    with pytest.raises(AuthError):
        await store.authenticate("u2", "pw")


async def test_create_account_persists_hash_not_plaintext():
    pool = FakePgPool(row=None)
    store = AccountStore(pg_pool=pool, settings=Settings())
    account = await store.create_account(username="newuser", password="plain-text-pw", role="teacher")
    assert isinstance(account, Account)
    assert account.user_id == "newuser"
    assert account.role == "teacher"
    assert verify_password("plain-text-pw", account.password_hash)
    # 写入 DB 的参数不能包含明文密码
    assert pool.conn.executed, "expected an INSERT execute call"
    for _query, args in pool.conn.executed:
        assert "plain-text-pw" not in args
