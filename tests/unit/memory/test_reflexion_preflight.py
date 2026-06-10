from __future__ import annotations

import pytest

import reflexlearn.common.embedding as emb
from reflexlearn.memory.reflexion import recall_reflections


class _MissingCollectionQdrant:
    def __init__(self):
        self.queries = 0
        self.scrolls = 0

    async def collection_exists(self, collection_name: str) -> bool:
        return False

    async def query_points(self, **kwargs):
        self.queries += 1
        raise AssertionError("query_points should not run without collection")

    async def scroll(self, **kwargs):
        self.scrolls += 1
        raise AssertionError("scroll should not run without collection")


@pytest.mark.asyncio
async def test_recall_skips_embedding_when_collection_missing(monkeypatch):
    called = {"embedding": 0}

    def embed_query(_query: str):
        called["embedding"] += 1
        raise AssertionError("embedding should not load before qdrant is ready")

    fake = _MissingCollectionQdrant()
    monkeypatch.setattr(emb, "embed_query", embed_query)

    res = await recall_reflections(
        qdrant=fake,
        task_type="doc",
        query="线性回归",
        acl={"user_id": "u1"},
    )

    assert res == []
    assert called["embedding"] == 0
    assert fake.queries == 0
    assert fake.scrolls == 0
