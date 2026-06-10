"""W3-D 上传隔离区 + 扫描占位。

上传先入 quarantined → 规则扫描（可执行魔数 / 危险 HTML script）→ accepted/rejected。
扫描是占位规则引擎（非企业级杀毒）；store 依赖注入 pg_pool，不可用退进程内存。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

QUARANTINED = "quarantined"
SCANNED = "scanned"
ACCEPTED = "accepted"
REJECTED = "rejected"
EXPIRED = "expired"

_EXECUTABLE_MAGIC = (b"MZ", b"\x7fELF", b"\xca\xfe\xba\xbe", b"\xfe\xed\xfa")
_DANGEROUS_HTML = [
    re.compile(r"<script\b", re.I),
    re.compile(r"javascript:", re.I),
    re.compile(r"<iframe\b", re.I),
    re.compile(r"\son(load|error|click|mouseover)\s*=", re.I),
]


class UploadObject(BaseModel):
    object_id: str
    user_id: str
    tenant_id: str
    original_name: str
    status: str = QUARANTINED
    sha256: str = ""
    size: int = 0
    content_type: str = ""
    storage_key: str = ""
    reasons: list[str] = Field(default_factory=list)


def scan_upload(*, raw: bytes, extension: str) -> list[str]:
    """占位扫描：可执行魔数 + 危险 HTML/script。返回拒绝原因（空=通过）。

    仅对 html/htm 检查 script 注入（会被浏览器执行）；md/txt 等纯文本中的代码块
    不视为危险，避免误伤正常学习资料。
    """
    reasons: list[str] = []
    if any(raw[:8].startswith(magic) for magic in _EXECUTABLE_MAGIC):
        reasons.append("executable_content")
    if extension in {"html", "htm"}:
        text = raw[:65536].decode("utf-8", errors="ignore")
        if any(p.search(text) for p in _DANGEROUS_HTML):
            reasons.append("dangerous_html")
    return reasons


class UploadQuarantineStore:
    def __init__(self, *, pg_pool: Any = None) -> None:
        self._pg = pg_pool
        self._mem: dict[str, UploadObject] = {}

    async def register(
        self,
        *,
        user_id: str,
        tenant_id: str,
        original_name: str,
        raw: bytes,
        content_type: str,
    ) -> UploadObject:
        obj = UploadObject(
            object_id=uuid.uuid4().hex,
            user_id=user_id,
            tenant_id=tenant_id,
            original_name=original_name,
            sha256=hashlib.sha256(raw).hexdigest(),
            size=len(raw),
            content_type=content_type,
            storage_key=f"quarantine/{tenant_id}/{uuid.uuid4().hex}",
        )
        await self._persist(obj)
        return obj

    async def mark(self, obj: UploadObject, status: str, reasons: list[str] | None = None) -> UploadObject:
        obj.status = status
        if reasons:
            obj.reasons = list(reasons)
        await self._persist(obj)
        return obj

    async def get(self, object_id: str) -> UploadObject | None:
        if self._pg is not None:
            try:
                async with self._pg.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM upload_objects WHERE object_id=$1", object_id
                    )
                if row:
                    return _row_to_object(row)
            except Exception:  # noqa: BLE001
                pass
        return self._mem.get(object_id)

    async def _persist(self, obj: UploadObject) -> None:
        self._mem[obj.object_id] = obj
        if self._pg is None:
            return
        try:
            async with self._pg.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO upload_objects (
                        object_id, user_id, tenant_id, original_name, status,
                        sha256, size, content_type, storage_key, reasons
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
                    ON CONFLICT (object_id) DO UPDATE SET
                        status=EXCLUDED.status, reasons=EXCLUDED.reasons
                    """,
                    obj.object_id,
                    obj.user_id,
                    obj.tenant_id,
                    obj.original_name,
                    obj.status,
                    obj.sha256,
                    obj.size,
                    obj.content_type,
                    obj.storage_key,
                    json.dumps(obj.reasons, ensure_ascii=False),
                )
        except Exception as exc:  # noqa: BLE001 - 隔离落库失败不阻断主链路
            logger.info("upload quarantine persist degraded: %s", exc)


def _row_to_object(row) -> UploadObject:
    data = dict(row)
    reasons = data.get("reasons") or []
    if isinstance(reasons, str):
        try:
            reasons = json.loads(reasons)
        except Exception:  # noqa: BLE001
            reasons = []
    return UploadObject(
        object_id=data["object_id"],
        user_id=data["user_id"],
        tenant_id=data["tenant_id"],
        original_name=data["original_name"],
        status=data.get("status") or QUARANTINED,
        sha256=data.get("sha256") or "",
        size=data.get("size") or 0,
        content_type=data.get("content_type") or "",
        storage_key=data.get("storage_key") or "",
        reasons=reasons,
    )
