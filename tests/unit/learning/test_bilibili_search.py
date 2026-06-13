import httpx
import pytest

from reflexlearn.learning.bilibili_search import (
    BiliSearchClient,
    BiliVideo,
    mixin_key,
    parse_duration_minutes,
    parse_search_payload,
    sign_params,
)
from reflexlearn.learning.resource_discovery import (
    DiscoverResourceRequest,
    build_resource_discovery,
    merge_live_videos,
)


def test_mixin_key_applies_permutation_table():
    raw = "".join(chr(ord("a") + i % 26) for i in range(64))
    key = mixin_key(raw[:32], raw[32:])

    assert len(key) == 32
    assert key[0] == raw[46]
    assert key[1] == raw[47]


def test_sign_params_appends_wts_and_w_rid():
    signed = sign_params({"keyword": "线性回归", "page": 1}, "k" * 32, now=1700000000)

    assert signed["wts"] == 1700000000
    assert len(signed["w_rid"]) == 32
    assert signed["keyword"] == "线性回归"


def test_parse_duration_minutes_handles_hms_and_garbage():
    assert parse_duration_minutes("43:52") == 44
    assert parse_duration_minutes("1:02:30") == 63
    assert parse_duration_minutes("") == 10
    assert parse_duration_minutes("abc") == 10


def test_parse_search_payload_extracts_videos_and_strips_em_tags():
    payload = {
        "code": 0,
        "data": {
            "result": [
                {
                    "bvid": "BV1xx",
                    "title": '<em class="keyword">线性回归</em>入门',
                    "author": "一数",
                    "duration": "10:00",
                    "description": "d",
                },
                {"bvid": "", "title": "no bvid skipped"},
            ]
        },
    }

    videos = parse_search_payload(payload, limit=5)

    assert len(videos) == 1
    assert videos[0].title == "线性回归入门"
    assert videos[0].duration_minutes == 10


def test_parse_search_payload_raises_on_error_code():
    with pytest.raises(ValueError):
        parse_search_payload({"code": -412}, limit=5)


async def test_search_videos_caches_and_rate_limits(monkeypatch):
    client = BiliSearchClient()
    calls = {"n": 0}

    async def fake_fetch(keyword):
        calls["n"] += 1
        return [BiliVideo(title="t", bvid="BV1")]

    async def fake_ensure_client():
        return None

    async def fake_ensure_key(_client):
        return "k" * 32

    monkeypatch.setattr(client, "_ensure_client", fake_ensure_client)
    monkeypatch.setattr(client, "_ensure_wbi_key", fake_ensure_key)

    transport_calls = {"n": 0}

    async def fake_get(url, params=None):
        transport_calls["n"] += 1
        return httpx.Response(
            200,
            json={"code": 0, "data": {"result": [{"bvid": "BV1", "title": "t", "duration": "5:00"}]}},
            request=httpx.Request("GET", url),
        )

    class FakeHttp:
        get = staticmethod(fake_get)

    async def ensure_fake():
        return FakeHttp()

    monkeypatch.setattr(client, "_ensure_client", ensure_fake)

    import reflexlearn.learning.bilibili_search as bili

    first = await bili._original_search_videos(client, "线性回归")
    second = await bili._original_search_videos(client, "线性回归")

    assert first and second
    assert transport_calls["n"] == 1  # 第二次命中关键词缓存，不再外呼


async def test_search_videos_returns_none_on_any_failure(monkeypatch):
    client = BiliSearchClient()

    async def boom():
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "_ensure_client", boom)

    import reflexlearn.learning.bilibili_search as bili

    assert await bili._original_search_videos(client, "线性回归") is None
    assert await bili._original_search_videos(client, "") is None


def test_merge_live_videos_replaces_static_bilibili_keeps_others():
    req = DiscoverResourceRequest(goal="线性回归入门", weak_points=["损失函数"])
    base = build_resource_discovery(req)
    videos = [
        BiliVideo(title="真实视频 A", bvid="BV1A", author="一数", duration_minutes=44),
        BiliVideo(title="真实视频 B", bvid="BV1B", duration_minutes=20),
    ]

    merged = merge_live_videos(base, videos, req)

    ids = [item.resource_id for item in merged.items]
    assert "candidate-bilibili-BV1A" in ids
    assert all(not i.startswith("candidate-bilibili-损") for i in ids)
    live = next(item for item in merged.items if item.resource_id == "candidate-bilibili-BV1A")
    assert live.href == "https://www.bilibili.com/video/BV1A"
    assert live.usage_mode == "metadata_only"
    assert live.source_policy == "embed_or_redirect_only"
    assert "UP 主 一数" in live.reason
    assert any(item.provider != "Bilibili" for item in merged.items)  # 其他 provider 保留
    assert "bilibili:live" in merged.degraded


def test_merge_live_videos_noop_without_videos():
    req = DiscoverResourceRequest(goal="g")
    base = build_resource_discovery(req)

    assert merge_live_videos(base, [], req) is base


def test_discovery_query_combines_goal_and_topic():
    from reflexlearn.learning.resource_discovery import discovery_query

    combo = DiscoverResourceRequest(goal="线性回归入门", weak_points=["数学推导"])
    assert discovery_query(combo) == "线性回归入门 数学推导"

    plain = DiscoverResourceRequest(goal="线性回归入门")
    assert discovery_query(plain) == "线性回归入门"
