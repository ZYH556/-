from __future__ import annotations

import builtins

import pytest

from reflexlearn.rag.keyword import KeywordIndex, _tokenize


class _Point:
    def __init__(self, id, payload):
        self.id = id
        self.payload = payload


class _FakeQdrant:
    def __init__(self, points):
        self._points = points

    async def scroll(self, **kwargs):
        return self._points, None  # 一次返回全部，next_offset=None


def _pts():
    return [
        _Point("id1", {"content": "线性回归用最小二乘法求解参数", "source": "lr.md",
                       "visibility": "public", "source_trust": 0.9}),
        _Point("id2", {"content": "梯度下降通过迭代最小化损失函数", "source": "gd.md",
                       "visibility": "public", "source_trust": 0.8}),
        _Point("id3", {"content": "私有笔记神经网络调参技巧与经验", "source": "note.md",
                       "visibility": "private", "user_id": "other", "source_trust": 0.5}),
    ]


@pytest.fixture(autouse=True)
def _reset_index():
    KeywordIndex.invalidate()
    yield
    KeywordIndex.invalidate()


def test_tokenize_nonempty():
    """中文分词（jieba 或 bigram）应切出非空 token。"""
    toks = _tokenize("线性回归与梯度下降")
    assert toks


def test_tokenize_bigram_fallback(monkeypatch):
    """jieba 不可用 → 字符 bigram 回退。"""
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "jieba":
            raise ImportError("no jieba")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    toks = _tokenize("线性回归")
    assert toks == ["线性", "性回", "回归"]


@pytest.mark.asyncio
async def test_keyword_search_aligns_point_id(monkeypatch):
    """BM25 命中结果的 chunk_id 与注入的 qdrant point.id 对齐。"""
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant(_pts()))
    idx = await KeywordIndex.get()
    assert idx is not None
    hits = idx.search("线性回归最小二乘", top_k=5,
                      acl={"tenant_id": "default", "visibility": ["public"]})
    assert hits
    assert hits[0].chunk_id == "id1"
    assert hits[0].origin == "keyword"
    assert hits[0].source_trust == 0.9


@pytest.mark.asyncio
async def test_keyword_acl_filters_private(monkeypatch):
    """命中私有 chunk 但 ACL 非本人 → 被过滤掉。"""
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant(_pts()))
    idx = await KeywordIndex.get()
    hits = idx.search("神经网络调参技巧", top_k=5, acl={"user_id": "me", "tenant_id": "default"})
    assert all(h.chunk_id != "id3" for h in hits)


@pytest.mark.asyncio
async def test_keyword_index_none_when_bm25_missing(monkeypatch):
    """rank_bm25 缺失 → KeywordIndex.get() 返回 None（keyword 路跳过）。"""
    monkeypatch.setattr("reflexlearn.common.db.get_qdrant", lambda: _FakeQdrant(_pts()))
    real_import = builtins.__import__

    def fake_import(name, *a, **k):
        if name == "rank_bm25":
            raise ImportError("no rank_bm25")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    idx = await KeywordIndex.get()
    assert idx is None
