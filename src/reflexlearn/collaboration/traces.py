from __future__ import annotations

import json
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class CollaborationTraceEvent(BaseModel):
    trace_id: str
    user_id: str
    tenant_id: str
    session_id: str
    node: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: float = 0.0


class TraceList(BaseModel):
    items: list[CollaborationTraceEvent] = Field(default_factory=list)
    degraded: list[str] = Field(default_factory=list)


class CollaborationTraceStore:
    def __init__(self, *, pg_pool=None) -> None:
        self._pg_pool = pg_pool
        self._mem: list[CollaborationTraceEvent] = []

    def record_memory(
        self,
        *,
        user_id: str,
        tenant_id: str,
        session_id: str,
        node: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> CollaborationTraceEvent:
        event = _event(
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            node=node,
            event_type=event_type,
            payload=payload or {},
        )
        self._mem.append(event)
        return event

    def list_memory(
        self,
        *,
        user_id: str,
        tenant_id: str,
        limit: int,
    ) -> list[CollaborationTraceEvent]:
        items = [
            item
            for item in self._mem
            if item.user_id == user_id and item.tenant_id == tenant_id
        ]
        items.sort(key=lambda item: item.created_at, reverse=True)
        return items[:limit]

    async def record(
        self,
        *,
        user_id: str,
        tenant_id: str,
        session_id: str,
        node: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        pg_pool=None,
    ) -> CollaborationTraceEvent:
        event = _event(
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            node=node,
            event_type=event_type,
            payload=payload or {},
        )
        pool = pg_pool or self._pg_pool
        if pool is None:
            self._mem.append(event)
            return event
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO collaboration_traces (
                        trace_id, user_id, tenant_id, session_id, node, event_type, payload
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb)
                    """,
                    event.trace_id,
                    event.user_id,
                    event.tenant_id,
                    event.session_id,
                    event.node,
                    event.event_type,
                    json.dumps(event.payload, ensure_ascii=False),
                )
        except Exception:
            self._mem.append(event)
        return event

    async def list_for_user(
        self,
        *,
        user_id: str,
        tenant_id: str,
        pg_pool=None,
        limit: int = 50,
    ) -> TraceList:
        pool = pg_pool or self._pg_pool
        if pool is not None:
            try:
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT * FROM collaboration_traces
                        WHERE user_id=$1 AND tenant_id=$2
                        ORDER BY created_at DESC
                        LIMIT $3
                        """,
                        user_id,
                        tenant_id,
                        limit,
                    )
                return TraceList(items=[_row_to_event(row) for row in rows])
            except Exception:
                pass
        return TraceList(
            items=self.list_memory(user_id=user_id, tenant_id=tenant_id, limit=limit),
            degraded=["pg:unavailable"],
        )


_default_store = CollaborationTraceStore()


def get_default_trace_store() -> CollaborationTraceStore:
    return _default_store


def reset_default_trace_store() -> None:
    global _default_store
    _default_store = CollaborationTraceStore()


def _event(
    *,
    user_id: str,
    tenant_id: str,
    session_id: str,
    node: str,
    event_type: str,
    payload: dict[str, Any],
) -> CollaborationTraceEvent:
    return CollaborationTraceEvent(
        trace_id=uuid.uuid4().hex,
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        node=node,
        event_type=event_type,
        payload=payload,
        created_at=time.time(),
    )


def _row_to_event(row) -> CollaborationTraceEvent:
    data = dict(row)
    payload = data.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}
    created = data.get("created_at")
    created_at = created.timestamp() if hasattr(created, "timestamp") else time.time()
    return CollaborationTraceEvent(
        trace_id=data["trace_id"],
        user_id=data["user_id"],
        tenant_id=data["tenant_id"],
        session_id=data["session_id"],
        node=data["node"],
        event_type=data["event_type"],
        payload=payload,
        created_at=created_at,
    )
