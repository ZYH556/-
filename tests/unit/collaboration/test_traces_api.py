from fastapi.testclient import TestClient

import reflexlearn.api.routes.traces as route
import reflexlearn.common.db as db
from reflexlearn.api.app import create_app
from reflexlearn.collaboration.traces import CollaborationTraceStore
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def test_trace_store_memory_fallback_filters_by_owner():
    store = CollaborationTraceStore(pg_pool=None)
    first = store.record_memory(
        user_id="u1",
        tenant_id="t1",
        session_id="s1",
        node="planner",
        event_type="agent_step",
        payload={"detail": "planned"},
    )
    store.record_memory(
        user_id="u2",
        tenant_id="t1",
        session_id="s2",
        node="planner",
        event_type="agent_step",
        payload={"detail": "other"},
    )

    got = store.list_memory(user_id="u1", tenant_id="t1", limit=20)
    assert [item.trace_id for item in got] == [first.trace_id]


def test_trace_route_degrades_without_pg(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)
    route.reset_trace_store_for_tests()
    route.get_trace_store().record_memory(
        user_id="u1",
        tenant_id="default",
        session_id="s1",
        node="assemble",
        event_type="agent_step",
        payload={"detail": "done"},
    )

    client = TestClient(create_app())
    resp = client.get("/api/collaboration/traces", headers=_headers("u1"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["degraded"] == ["pg:unavailable"]
    assert len(body["items"]) == 1
    assert body["items"][0]["node"] == "assemble"
    route.reset_trace_store_for_tests()
