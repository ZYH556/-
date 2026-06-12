from fastapi.testclient import TestClient

import reflexlearn.api.routes.traces as route
from reflexlearn.api.app import create_app
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def test_lora_export_api_exports_only_current_user_traces(tmp_path, monkeypatch):
    monkeypatch.setattr(route, "lora_output_dir", lambda: tmp_path, raising=False)

    # hermetic：环境里 PG 可达时 safe_pg_pool 会真连，list_for_user 转读 PG
    # 而测试轨迹写在内存 store——强制 None 走内存路径，结果不随 Docker 状态漂移。
    async def no_pg():
        return None

    monkeypatch.setattr(route, "safe_pg_pool", no_pg)
    route.reset_trace_store_for_tests()
    route.get_trace_store().record_memory(
        user_id="owner",
        tenant_id="default",
        session_id="s-owner",
        node="session_start",
        event_type="agent_step",
        payload={"message": "学习 RAG ACL，Authorization=Bearer secret-token"},
    )
    route.get_trace_store().record_memory(
        user_id="owner",
        tenant_id="default",
        session_id="s-owner",
        node="assemble",
        event_type="agent_step",
        payload={"total": 2},
    )
    route.get_trace_store().record_memory(
        user_id="other",
        tenant_id="default",
        session_id="s-other",
        node="session_start",
        event_type="agent_step",
        payload={"message": "other private goal"},
    )

    client = TestClient(create_app())
    exported = client.post("/api/growth/lora-samples/export", headers=_headers("owner"))
    assert exported.status_code == 200
    body = exported.json()
    assert body["sample_count"] == 1
    assert body["sanitized"] is True
    assert body["items"][0]["metadata"]["session_id"].startswith("sha256:")

    listed = client.get("/api/growth/lora-samples", headers=_headers("owner"))
    assert listed.status_code == 200
    assert listed.json()["items"][0]["sample_count"] == 1

    content = tmp_path.joinpath("lora_samples_latest.jsonl").read_text(encoding="utf-8")
    assert "owner" not in content
    assert "other private goal" not in content
    assert "secret-token" not in content
    route.reset_trace_store_for_tests()
