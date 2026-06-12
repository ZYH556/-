from reflexlearn.learning.demo_seed import build_demo_seed


def test_demo_seed_contains_learning_product_assets():
    seed = build_demo_seed(user_id="student-a", tenant_id="demo")

    assert len(seed.spaces) >= 5
    assert len(seed.resources) >= 20
    assert len(seed.mistakes) >= 10
    assert len(seed.profiles) >= 3
    assert any(item.type == "external_video" for item in seed.resources)
    assert any(item.provider == "Bilibili" for item in seed.resources)
    assert all(item.tenant_id == "demo" for item in seed.spaces)


def test_external_video_seed_uses_metadata_only_policy():
    seed = build_demo_seed(user_id="student-a", tenant_id="demo")
    videos = [item for item in seed.resources if item.type == "external_video"]

    assert videos
    assert all(item.provider == "Bilibili" for item in videos)
    assert all(item.source_label == "B 站视频" for item in videos)
    assert all(item.usage_mode == "metadata_only" for item in videos)
    assert all(item.source_policy == "embed_or_redirect_only" for item in videos)
    assert all(item.href.startswith("https://") for item in videos)


def test_demo_seed_user_and_tenant_are_consistent():
    seed = build_demo_seed(user_id="student-a", tenant_id="demo")

    assert all(item.user_id == "student-a" for item in seed.spaces)
    assert all(item.tenant_id == "demo" for item in seed.resources)
    assert all(item.user_id == "student-a" for item in seed.mistakes)
    assert any(item.user_id == "student-a" for item in seed.profiles)
