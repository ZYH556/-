import httpx

from reflexlearn.learning.mdn_search import (
    MdnDoc,
    MdnSearchClient,
    parse_mdn_payload,
)
from reflexlearn.learning.resource_discovery import (
    DiscoverResourceRequest,
    build_resource_discovery,
    merge_live_docs,
)

PAYLOAD = {
    "documents": [
        {
            "title": "Promise",
            "mdn_url": "/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Promise",
            "summary": "Promise 对象用于异步计算。",
            "score": 50.9,
        },
        {
            "title": "低相关",
            "mdn_url": "/zh-CN/docs/Other",
            "summary": "noise",
            "score": 1.0,
        },
        {"title": "", "mdn_url": "/x", "score": 99},
    ]
}


def test_parse_mdn_payload_filters_low_score_and_builds_absolute_url():
    docs = parse_mdn_payload(PAYLOAD, limit=5)

    assert len(docs) == 1  # 低分 + 空标题被过滤
    assert docs[0].title == "Promise"
    assert docs[0].url == (
        "https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Promise"
    )
    assert docs[0].score == 50.9


def test_parse_mdn_payload_empty_documents():
    assert parse_mdn_payload({"documents": []}, limit=5) == []
    assert parse_mdn_payload({}, limit=5) == []


async def test_search_docs_caches_and_returns_none_when_empty(monkeypatch):
    client = MdnSearchClient()
    transport_calls = {"n": 0}

    async def fake_get(url, params=None):
        transport_calls["n"] += 1
        return httpx.Response(200, json=PAYLOAD, request=httpx.Request("GET", url))

    class FakeHttp:
        get = staticmethod(fake_get)

    async def ensure_fake():
        return FakeHttp()

    monkeypatch.setattr(client, "_ensure_client", ensure_fake)

    import reflexlearn.learning.mdn_search as mdn

    first = await mdn._original_search_docs(client, "Promise")
    second = await mdn._original_search_docs(client, "Promise")

    assert first and first[0].title == "Promise"
    assert second is not None
    assert transport_calls["n"] == 1  # 第二次命中缓存


async def test_search_docs_returns_none_on_failure(monkeypatch):
    client = MdnSearchClient()

    async def boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "_ensure_client", boom)

    import reflexlearn.learning.mdn_search as mdn

    assert await mdn._original_search_docs(client, "Promise") is None
    assert await mdn._original_search_docs(client, "") is None


def test_merge_live_docs_replaces_static_official_keeps_others():
    req = DiscoverResourceRequest(goal="JavaScript 异步", weak_points=["Promise"])
    base = build_resource_discovery(req)
    docs = [
        MdnDoc(
            title="Promise",
            url="https://developer.mozilla.org/zh-CN/docs/Web/JavaScript/Reference/Global_Objects/Promise",
            summary="异步计算",
            score=50,
        )
    ]

    merged = merge_live_docs(base, docs, req)

    ids = [item.resource_id for item in merged.items]
    mdn_ids = [i for i in ids if i.startswith("candidate-mdn-")]
    assert len(mdn_ids) == 1  # candidate_id 用 url 短 hash（稳定、防尾段碰撞）
    # 静态 official_doc 候选（scikit-learn/pytorch）被替换
    assert all(not i.startswith("candidate-scikit-learn-") for i in ids)
    assert all(not i.startswith("candidate-pytorch-") for i in ids)
    mdn_item = next(i for i in merged.items if i.resource_id in mdn_ids)
    assert mdn_item.provider == "MDN"
    assert mdn_item.source_label == "官方文档"
    # 其他 provider（B 站静态 / 公开课）保留
    assert any(i.provider not in ("MDN",) for i in merged.items)
    assert "mdn:live" in merged.degraded


def test_merge_live_docs_id_is_stable_and_distinct_per_url():
    req = DiscoverResourceRequest(goal="JavaScript", weak_points=["Promise"])
    base = build_resource_discovery(req)
    docs = [
        MdnDoc(title="A", url="https://developer.mozilla.org/zh-CN/docs/Web/X/Promise", score=40),
        MdnDoc(title="B", url="https://developer.mozilla.org/zh-CN/docs/Web/Y/Promise", score=39),
    ]

    first = merge_live_docs(base, docs, req)
    second = merge_live_docs(base, docs, req)

    ids1 = sorted(i.resource_id for i in first.items if i.resource_id.startswith("candidate-mdn-"))
    ids2 = sorted(i.resource_id for i in second.items if i.resource_id.startswith("candidate-mdn-"))
    assert len(ids1) == 2  # 同尾段 Promise 不再碰撞
    assert ids1 == ids2  # 同 url 每次同 id（稳定，保存幂等可靠）


def test_merge_live_docs_noop_without_docs():
    req = DiscoverResourceRequest(goal="g")
    base = build_resource_discovery(req)

    assert merge_live_docs(base, [], req) is base


def test_is_web_topic_gates_non_web_queries():
    from reflexlearn.learning.mdn_search import is_web_topic

    assert is_web_topic("JavaScript 异步编程 Promise")
    assert is_web_topic("前端工程能力提升")
    assert is_web_topic("React 状态管理")
    assert not is_web_topic("线性回归入门 数学推导")
    assert not is_web_topic("机器学习 梯度下降")
