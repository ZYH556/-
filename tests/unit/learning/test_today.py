from reflexlearn.learning.today import (
    TodayLearningPathNode,
    TodayResource,
    TodaySummary,
    build_today_summary,
)


def test_build_today_summary_prefers_current_space_and_open_mistakes():
    summary = build_today_summary(
        user_id="student-a",
        spaces=[
            {"space_id": "space-1", "title": "机器学习基础强化", "status": "active"},
        ],
        resources=[
            {
                "resource_id": "res-1",
                "type": "external_video",
                "title": "线性回归损失函数讲解",
                "provider": "Bilibili",
                "source_label": "B 站视频",
                "estimated_minutes": 14,
                "href": "https://www.bilibili.com/video/BVdemo",
            }
        ],
        mistakes=[
            {"mistake_id": "m-1", "concept": "损失函数", "status": "open"},
            {"mistake_id": "m-2", "concept": "梯度方向", "status": "open"},
        ],
        profile={
            "goal": "掌握线性回归与梯度下降",
            "weak_points": ["损失函数", "梯度方向"],
            "preferences": {"resource_mix": "视频讲解 + 五题短练习"},
            "progress": 0.62,
        },
    )

    assert isinstance(summary, TodaySummary)
    assert summary.current_goal == "掌握线性回归与梯度下降"
    assert summary.main_task.title == "先补齐损失函数，再进入梯度下降练习"
    assert summary.main_task.space_id == "space-1"
    assert summary.resources[0].type == "external_video"
    assert summary.review_queue[0].topic == "损失函数"
    assert summary.profile_signals[0].label == "学习偏好"


def test_today_resource_accepts_external_video_metadata():
    resource = TodayResource(
        id="bv-linear-loss",
        type="external_video",
        title="线性回归损失函数讲解",
        provider="Bilibili",
        source_label="B 站视频",
        estimated_minutes=14,
        reason="先用视频建立代价曲线直觉。",
        href="https://www.bilibili.com/video/BVdemo",
        embed_url="https://player.bilibili.com/player.html?bvid=BVdemo",
        usage_mode="metadata_only",
        source_policy="embed_or_redirect_only",
    )

    assert resource.usage_mode == "metadata_only"
    assert resource.source_policy == "embed_or_redirect_only"


def test_learning_path_node_status_is_constrained():
    node = TodayLearningPathNode(
        id="loss-function",
        title="损失函数",
        status="current",
        summary="正在补齐代价含义与误差平方和。",
    )

    assert node.status == "current"
