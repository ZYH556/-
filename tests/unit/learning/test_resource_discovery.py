from reflexlearn.learning.resource_discovery import (
    DiscoverResourceRequest,
    build_resource_discovery,
)


def test_resource_discovery_returns_metadata_only_external_candidates():
    result = build_resource_discovery(
        DiscoverResourceRequest(
            goal="掌握线性回归与梯度下降",
            weak_points=["损失函数", "梯度方向"],
            providers=["bilibili", "official_doc", "oer"],
            limit=6,
        )
    )

    providers = {item.provider for item in result.items}
    assert {"Bilibili", "scikit-learn", "Coursera"}.issubset(providers)
    assert result.query.goal == "掌握线性回归与梯度下降"
    assert result.query.weak_points == ["损失函数", "梯度方向"]

    bilibili = next(item for item in result.items if item.provider == "Bilibili")
    assert bilibili.type == "external_video"
    assert bilibili.source_label == "B 站视频"
    assert bilibili.usage_mode == "metadata_only"
    assert bilibili.source_policy == "embed_or_redirect_only"
    assert bilibili.href.startswith("https://search.bilibili.com/")
    assert bilibili.embed_url == ""
    assert "下载" not in bilibili.reason


def test_resource_discovery_limit_and_default_provider_policy():
    result = build_resource_discovery(
        DiscoverResourceRequest(
            goal="Python 数据分析入门",
            weak_points=[],
            providers=[],
            limit=2,
        )
    )

    assert len(result.items) == 2
    assert result.query.providers == ["bilibili", "official_doc", "oer"]
    assert all(item.usage_mode == "metadata_only" for item in result.items)
