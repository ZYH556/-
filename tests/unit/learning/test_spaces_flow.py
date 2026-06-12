"""学习空间闭环测试：创建 → 会话产出沉淀 → 聚合详情 + API ACL。"""

from fastapi.testclient import TestClient

import reflexlearn.common.db as db
from reflexlearn.api.app import create_app
from reflexlearn.api.routes.chat import _persist_outcome
from reflexlearn.common.auth import CurrentUser, issue_token
from reflexlearn.common.config import Settings
from reflexlearn.learning.spaces import (
    SessionOutcome,
    SpaceStore,
    get_space_store,
    reset_space_store_for_tests,
)


def _headers(user_id: str, tenant_id: str = "default") -> dict[str, str]:
    token = issue_token(
        CurrentUser(user_id=user_id, tenant_id=tenant_id, role="student"),
        Settings(),
    )
    return {"Authorization": f"Bearer {token}"}


def _block_pg(monkeypatch):
    async def _no_pg():
        raise RuntimeError("pg disabled in unit tests")

    monkeypatch.setattr(db, "get_pg_pool", _no_pg)


async def test_create_space_memory_fallback():
    store = SpaceStore()
    space = await store.create_space(
        user_id="u1", tenant_id="default", title="线性回归目标", pg_pool=None
    )
    assert space.space_id == "mem-1"
    assert space.title == "线性回归目标"
    assert "pg:unavailable" in space.degraded


async def test_save_outcome_then_detail_memory_roundtrip():
    store = SpaceStore()
    space = await store.create_space(
        user_id="u1", tenant_id="default", title="梯度下降", pg_pool=None
    )
    outcome = SessionOutcome(
        resources=[
            {"type": "doc", "content": "讲解" * 30, "concept": "梯度下降", "title": "梯度下降"},
            {"type": "quiz", "content": "题目" * 30, "concept": "梯度下降", "title": "梯度下降"},
        ],
        path_steps=[
            {"sequence": 1, "task_id": "t1", "resource_type": "doc", "concept": "梯度下降",
             "objective": "理解原理", "rationale": "先讲解", "difficulty": 0.3},
            {"sequence": 2, "task_id": "t2", "resource_type": "quiz", "concept": "梯度下降",
             "objective": "练习巩固", "rationale": "后练习", "difficulty": 0.5},
        ],
        path_summary="先理解后练习",
        path_strategy="rule",
    )
    saved = await store.save_session_outcome(
        space_id=space.space_id, user_id="u1", tenant_id="default",
        outcome=outcome, pg_pool=None,
    )
    assert saved["resources_saved"] == 2
    assert saved["path_saved"] is True

    detail = await store.get_space_detail(space.space_id, pg_pool=None)
    assert detail is not None
    assert detail.path_summary == "先理解后练习"
    assert [s.sequence for s in detail.steps] == [1, 2]
    assert {r.type for r in detail.resources} == {"doc", "quiz"}


async def test_detail_missing_space_returns_none():
    store = SpaceStore()
    assert await store.get_space_detail("nope", pg_pool=None) is None


async def test_space_api_create_and_detail_acl(monkeypatch):
    _block_pg(monkeypatch)
    reset_space_store_for_tests()
    client = TestClient(create_app())

    created = client.post(
        "/api/spaces", json={"title": "考研数学"}, headers=_headers("u1")
    )
    assert created.status_code == 200
    space_id = created.json()["space_id"]

    ok = client.get(f"/api/spaces/{space_id}/detail", headers=_headers("u1"))
    assert ok.status_code == 200
    assert ok.json()["title"] == "考研数学"

    assert client.get(f"/api/spaces/{space_id}/detail", headers=_headers("u2")).status_code == 403
    assert client.get("/api/spaces/ghost/detail", headers=_headers("u1")).status_code == 404
    reset_space_store_for_tests()


async def test_chat_persist_outcome_autocreates_space():
    reset_space_store_for_tests()
    saved = await _persist_outcome(
        space_id="",
        message="学习线性代数",
        user_id="u9",
        tenant_id="default",
        final_resources=[{"type": "doc", "task_id": "t1", "content": "内容" * 40}],
        final_path={
            "steps": [
                {"sequence": 1, "task_id": "t1", "resource_type": "doc",
                 "concept": "线性代数", "objective": "", "rationale": "", "difficulty": 0.3}
            ],
            "summary": "s",
            "strategy": "rule",
        },
        pg_pool=None,
    )
    assert saved is not None
    assert saved["resources_saved"] == 1
    assert saved["path_saved"] is True

    detail = await get_space_store().get_space_detail(saved["space_id"], pg_pool=None)
    assert detail is not None
    assert detail.title == "学习线性代数"
    # task_id 关联的 concept 回填到资源
    assert detail.resources[0].concept == "线性代数"
    reset_space_store_for_tests()


async def test_chat_persist_outcome_skips_when_empty():
    saved = await _persist_outcome(
        space_id="",
        message="随便聊聊",
        user_id="u9",
        tenant_id="default",
        final_resources=[],
        final_path={},
        pg_pool=None,
    )
    assert saved is None
