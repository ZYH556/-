"""W3-B: 审计日志（PG 写入，不可用退结构化日志）。"""

from __future__ import annotations

from reflexlearn.security.audit import AuditEvent, AuditLog


class _FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple] = []

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
    def __init__(self) -> None:
        self.conn = _FakeConn()

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self.conn)


async def test_audit_without_pg_only_logs():
    log = AuditLog(pg_pool=None)
    await log.record(AuditEvent(event_type="auth.login", user_id="u1", status="ok"))
    # 不抛错即通过


async def test_audit_writes_to_pg():
    pool = FakePgPool()
    log = AuditLog(pg_pool=pool)
    await log.record(
        AuditEvent(
            event_type="auth.login",
            user_id="u1",
            tenant_id="t1",
            ip="1.2.3.4",
            status="failed",
            detail={"reason": "bad password"},
        )
    )
    assert pool.conn.executed
    query, args = pool.conn.executed[0]
    assert "audit_events" in query
    assert "auth.login" in args
    assert "failed" in args


async def test_audit_pg_failure_does_not_raise():
    class BrokenPool:
        def acquire(self):
            raise RuntimeError("pg down")

    log = AuditLog(pg_pool=BrokenPool())
    await log.record(AuditEvent(event_type="auth.login", status="ok"))
    # 审计失败不抛错、不阻断主链路
