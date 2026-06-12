from reflexlearn.learning.assets import LearningAssetStore, LearningResource


def test_learning_resource_accepts_external_video_metadata():
    resource = LearningResource(
        resource_id="bv-loss",
        user_id="student-a",
        tenant_id="demo",
        type="external_video",
        title="线性回归损失函数讲解",
        provider="Bilibili",
        source_label="B 站视频",
        href="https://www.bilibili.com/video/BV1lossGuide",
        embed_url="https://player.bilibili.com/player.html?bvid=BV1lossGuide",
        usage_mode="metadata_only",
        source_policy="embed_or_redirect_only",
        estimated_minutes=14,
        reason="先用视频建立代价曲线直觉。",
    )

    assert resource.provider == "Bilibili"
    assert resource.source_label == "B 站视频"
    assert resource.usage_mode == "metadata_only"
    assert resource.source_policy == "embed_or_redirect_only"
    assert resource.embed_url.startswith("https://player.bilibili.com/")


def test_learning_resource_defaults_metadata_when_missing():
    resource = LearningResource(
        resource_id="res-plain",
        user_id="student-a",
        tenant_id="demo",
        type="ai_document",
    )

    assert resource.provider == ""
    assert resource.source_label == ""
    assert resource.href == ""
    assert resource.embed_url == ""
    assert resource.usage_mode == "personal"
    assert resource.source_policy == "owned_or_generated"
    assert resource.estimated_minutes == 10
    assert resource.reason == ""


async def test_asset_store_memory_seed_accepts_bilibili_resource():
    store = LearningAssetStore()
    store.seed_memory(
        resources=[
            {
                "resource_id": "bv-loss",
                "user_id": "student-a",
                "tenant_id": "demo",
                "type": "external_video",
                "title": "损失函数视频讲解",
                "provider": "Bilibili",
                "source_label": "B 站视频",
                "href": "https://search.bilibili.com/all?keyword=损失函数",
                "embed_url": "https://player.bilibili.com/player.html?bvid=BV1lossGuide",
                "usage_mode": "metadata_only",
                "source_policy": "embed_or_redirect_only",
            }
        ]
    )

    listed = await store.list_resources(user_id="student-a", tenant_id="demo", pg_pool=None)

    assert listed.items[0].provider == "Bilibili"
    assert listed.items[0].usage_mode == "metadata_only"
    assert listed.items[0].source_policy == "embed_or_redirect_only"
