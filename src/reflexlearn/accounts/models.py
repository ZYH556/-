"""账户模型：DB users 表的强类型映射。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from reflexlearn.common.auth import Role


class Account(BaseModel):
    user_id: str
    tenant_id: str = "default"
    role: Role = "student"
    password_hash: str = ""
    password_alg: str = "pbkdf2_sha256"
    disabled: bool = False
    last_login_at: datetime | None = None
