from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.memory.reflexion import recall_reflections, write_reflection
from reflexlearn.orchestration.schemas import Reflection


def _reflection() -> Reflection:
    return Reflection(
        task_type="quiz",
        failure_type="format_error",
        cause="题目 JSON 格式不符合 schema",
        fix_strategy="改用标准 JSON 模板并显式校验字段",
        success=False,
    )


class _FakeQdrant:
    def __init__(self, hits=None):
        self._hits = hits or []
        self.upserts: list[dict] = []
        self.queries: list[dict] = []
        self.payload_updates: list[dict] = []

    async def upsert(self, **kwargs):
        self.upserts.append(kwargs)

    async def query_points(self, **kwargs):
        self.queries.append(kwargs)
        return _QueryResponse(self._hits)

    async def set_payload(self, **kwargs):
        self.payload_updates.append(kwargs)


class _Point:
    def __init__(self, point_id: str, payload: dict):
        self.id = point_id
        self.payload = payload


class _QueryResponse:
    def __init__(self, points):
        self.points = points


@pytest.mark.asyncio
async def test_write_reflection_payload_contains_lifecycle_fields(monkeypatch):
    """调用方传入时间戳 → Qdrant payload 写 created_at，并初始化 hit_count=0。"""
    monkeypatch.setattr(emb, "embed_documents", lambda texts: [[0.1] * emb.EMBED_DIM])
    qdrant = _FakeQdrant()

    ok = await write_reflection(
        pg_pool=None,
        qdrant=qdrant,
        reflection=_reflection(),
        user_id="u1",
        created_at="2026-06-09T00:00:00+00:00",
    )

    assert ok is True
    payload = qdrant.upserts[0]["points"][0].payload
    assert payload["created_at"] == "2026-06-09T00:00:00+00:00"
    assert payload["hit_count"] == 0


@pytest.mark.asyncio
async def test_recall_reflections_bumps_hit_count_for_reused_memory(monkeypatch):
    """召回命中经验 → best-effort 回写 hit_count+1，作为记忆巩固信号。"""
    monkeypatch.setattr(emb, "embed_query", lambda q: [0.1] * emb.EMBED_DIM)
    qdrant = _FakeQdrant(
        hits=[
            _Point(
                "p1",
                {
                    "user_id": "u1",
                    "task_type": "quiz",
                    "cause": "旧经验",
                    "fix_strategy": "复用模板",
                    "hit_count": 2,
                },
            )
        ]
    )

    recalled = await recall_reflections(
        qdrant=qdrant,
        task_type="quiz",
        query="线性回归测验",
        acl={"user_id": "u1"},
    )

    assert recalled[0]["cause"] == "旧经验"
    assert qdrant.payload_updates == [
        {
            "collection_name": "experience_memory",
            "payload": {"hit_count": 3},
            "points": ["p1"],
        }
    ]
