"""安全审计：关键事件写 audit_events 表，PG 不可用退结构化日志，绝不阻断主链路。"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("reflexlearn.audit")


class AuditEvent(BaseModel):
    event_type: str
    user_id: str = ""
    tenant_id: str = ""
    ip: str = ""
    object_type: str = ""
    object_id: str = ""
    status: str = "ok"
    detail: dict[str, Any] = Field(default_factory=dict)


class AuditLog:
    def __init__(self, *, pg_pool: Any = None) -> None:
        self._pg = pg_pool

    async def record(self, event: AuditEvent) -> None:
        # 始终留结构化日志，便于 PG 不可用时仍可审计。
        logger.info("audit %s", event.model_dump_json())
        if self._pg is None:
            return
        try:
            async with self._pg.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_events (
                        id, event_type, user_id, tenant_id, ip,
                        object_type, object_id, status, detail
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
                    """,
                    uuid.uuid4().hex,
                    event.event_type,
                    event.user_id,
                    event.tenant_id,
                    event.ip,
                    event.object_type,
                    event.object_id,
                    event.status,
                    json.dumps(event.detail, ensure_ascii=False),
                )
        except Exception:  # noqa: BLE001 - 审计失败不阻断主链路
            return
