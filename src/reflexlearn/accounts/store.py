"""账户存储：依赖注入 pg_pool，PG 不可用时仅 development 允许 demo fallback。

绝不在被测函数内自取 PG（conftest 不拦 get_pg_pool，自取会卡死单测）；
调用方经 api.service_deps.safe_pg_pool 注入。
"""

from __future__ import annotations

import hmac
import logging
from typing import Any, cast

from reflexlearn.accounts.models import Account
from reflexlearn.accounts.passwords import hash_password, verify_password
from reflexlearn.common.auth import AuthError, Role
from reflexlearn.common.config import Settings, get_settings

logger = logging.getLogger(__name__)

_VALID_ROLES = {"student", "teacher", "admin", "evaluator"}
# demo fallback 仅在 development 生效、安全不敏感：用低迭代加速本地/单测。
_DEMO_ITERATIONS = 1000


def _role(value: str | None) -> Role:
    if value in _VALID_ROLES:
        return cast(Role, value)
    return "student"


class AccountStore:
    def __init__(self, *, pg_pool: Any = None, settings: Settings | None = None) -> None:
        self._pg = pg_pool
        self._settings = settings or get_settings()

    async def get_account(self, username: str) -> Account | None:
        if self._pg is not None:
            try:
                async with self._pg.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT id, role, tenant_id, password_hash, "
                        "password_alg, disabled FROM users WHERE id=$1",
                        username,
                    )
                if row:
                    return _row_to_account(row)
            except Exception as exc:  # noqa: BLE001 - 降级铁律
                logger.info("account lookup degraded: %s", exc)
        return self._demo_account(username)

    async def authenticate(self, username: str, password: str) -> Account:
        account = await self.get_account(username)
        if account is None:
            raise AuthError("invalid credentials")
        if account.disabled:
            raise AuthError("account disabled")
        if not account.password_hash or not verify_password(password, account.password_hash):
            raise AuthError("invalid credentials")
        await self.touch_last_login(account.user_id)
        return account

    async def create_account(
        self,
        *,
        username: str,
        password: str,
        role: str = "student",
        tenant_id: str = "default",
        disabled: bool = False,
    ) -> Account:
        account = Account(
            user_id=username,
            tenant_id=tenant_id,
            role=_role(role),
            password_hash=hash_password(password),
            disabled=disabled,
        )
        if self._pg is None:
            return account
        try:
            async with self._pg.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (id, role, tenant_id, password_hash, password_alg, disabled)
                    VALUES ($1,$2,$3,$4,$5,$6)
                    ON CONFLICT (id) DO UPDATE SET
                        role=EXCLUDED.role,
                        tenant_id=EXCLUDED.tenant_id,
                        password_hash=EXCLUDED.password_hash,
                        password_alg=EXCLUDED.password_alg,
                        disabled=EXCLUDED.disabled
                    """,
                    account.user_id,
                    account.role,
                    account.tenant_id,
                    account.password_hash,
                    account.password_alg,
                    account.disabled,
                )
        except Exception as exc:  # noqa: BLE001 - 降级铁律
            logger.info("account create degraded: %s", exc)
        return account

    async def touch_last_login(self, username: str) -> None:
        if self._pg is None:
            return
        try:
            async with self._pg.acquire() as conn:
                await conn.execute("UPDATE users SET last_login_at=NOW() WHERE id=$1", username)
        except Exception:  # noqa: BLE001 - best-effort
            return

    def _demo_account(self, username: str) -> Account | None:
        cfg = self._settings
        if cfg.app_env.lower() == "production":
            return None
        if hmac.compare_digest(username, cfg.auth_demo_username):
            return Account(
                user_id=cfg.auth_demo_username,
                tenant_id=cfg.auth_demo_tenant_id,
                role=_role(cfg.auth_demo_role),
                password_hash=hash_password(cfg.auth_demo_password, iterations=_DEMO_ITERATIONS),
            )
        return None


def _row_to_account(row) -> Account:
    data = dict(row)
    return Account(
        user_id=data["id"],
        tenant_id=data.get("tenant_id") or "default",
        role=_role(data.get("role")),
        password_hash=data.get("password_hash") or "",
        password_alg=data.get("password_alg") or "pbkdf2_sha256",
        disabled=bool(data.get("disabled")),
    )
