from __future__ import annotations

import pytest

from reflexlearn.rag.retrieval.semantic import semantic_search


class _MissingCollectionQdrant:
    async def collection_exists(self, collection_name: str) -> bool:
        return False

    async def query_points(self, **kwargs):
        raise AssertionError("query_points should not run when collection is missing")


@pytest.mark.asyncio
async def test_semantic_skips_embedding_when_collection_missing(monkeypatch):
    called = {"embedding": 0}

    def embed_query(_query: str):
        called["embedding"] += 1
        raise AssertionError("embedding should not load before qdrant is ready")

    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _MissingCollectionQdrant())
    monkeypatch.setattr("reflexlearn.common.embedding.embed_query", embed_query)

    chunks = await semantic_search(
        "线性回归",
        {},
        5,
        "missing_collection",
        route_timeout_s=0.1,
    )

    assert chunks == []
    assert called["embedding"] == 0
