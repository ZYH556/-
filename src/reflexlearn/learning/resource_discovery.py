from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field, field_validator


ProviderKey = Literal["bilibili", "official_doc", "oer"]
ResourceKind = Literal["external_video", "official_doc", "oer"]
DEFAULT_PROVIDERS: list[ProviderKey] = ["bilibili", "official_doc", "oer"]


class DiscoverResourceRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=120)
    weak_points: list[str] = Field(default_factory=list)
    providers: list[ProviderKey] = Field(default_factory=list)
    limit: int = Field(default=9, ge=1, le=24)

    @field_validator("weak_points")
    @classmethod
    def trim_weak_points(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        return cleaned[:8]


class ResourceDiscoveryQuery(BaseModel):
    goal: str
    weak_points: list[str] = Field(default_factory=list)
    providers: list[ProviderKey] = Field(default_factory=list)


class ResourceCandidate(BaseModel):
    resource_id: str
    type: ResourceKind
    title: str
    content_preview: str
    provider: str
    source_label: str
    href: str
    embed_url: str = ""
    usage_mode: str = "metadata_only"
    source_policy: str = "embed_or_redirect_only"
    estimated_minutes: int
    reason: str
    matched_goal: str
    matched_weak_points: list[str] = Field(default_factory=list)
    rank_score: float


class ResourceDiscoveryResult(BaseModel):
    items: list[ResourceCandidate]
    query: ResourceDiscoveryQuery
    degraded: list[str] = Field(default_factory=list)


def build_resource_discovery(req: DiscoverResourceRequest) -> ResourceDiscoveryResult:
    providers = req.providers or DEFAULT_PROVIDERS
    weak_points = req.weak_points[:4]
    candidates: list[ResourceCandidate] = []
    for provider in providers:
        candidates.extend(_provider_candidates(provider, req.goal, weak_points))

    ranked = sorted(candidates, key=lambda item: item.rank_score, reverse=True)[: req.limit]
    return ResourceDiscoveryResult(
        items=ranked,
        query=ResourceDiscoveryQuery(
            goal=req.goal,
            weak_points=weak_points,
            providers=providers,
        ),
    )


def _provider_candidates(
    provider: ProviderKey,
    goal: str,
    weak_points: list[str],
) -> list[ResourceCandidate]:
    topic = _topic(goal, weak_points)
    if provider == "bilibili":
        return [_bilibili_candidate(goal, weak_points, topic)]
    if provider == "official_doc":
        return [
            _official_candidate(goal, weak_points, topic, "scikit-learn", 0.86),
            _official_candidate(goal, weak_points, topic, "PyTorch", 0.78),
        ]
    return [_oer_candidate(goal, weak_points, topic)]


def _bilibili_candidate(
    goal: str,
    weak_points: list[str],
    topic: str,
) -> ResourceCandidate:
    query = quote(f"{goal} {topic} 可视化讲解")
    return ResourceCandidate(
        resource_id=f"candidate-bilibili-{_slug(goal, topic)}",
        type="external_video",
        title=f"{topic} 可视化讲解",
        content_preview="来自 B 站搜索的候选视频方向，适合先建立直观理解。",
        provider="Bilibili",
        source_label="B 站视频",
        href=f"https://search.bilibili.com/all?keyword={query}",
        estimated_minutes=16,
        reason=f"围绕「{topic}」寻找直观讲解，先补感性理解，再回到练习和文档。",
        matched_goal=goal,
        matched_weak_points=weak_points,
        rank_score=0.92,
    )


def _official_candidate(
    goal: str,
    weak_points: list[str],
    topic: str,
    provider: str,
    score: float,
) -> ResourceCandidate:
    if provider == "scikit-learn":
        href = "https://scikit-learn.org/stable/modules/linear_model.html"
        title = "Linear Models 用户指南"
    else:
        href = "https://pytorch.org/tutorials/"
        title = f"{topic} 官方教程索引"
    return ResourceCandidate(
        resource_id=f"candidate-{provider.lower()}-{_slug(goal, topic)}",
        type="official_doc",
        title=title,
        content_preview="官方资料适合校准概念边界、API 用法和代码实践。",
        provider=provider,
        source_label="官方文档",
        href=href,
        estimated_minutes=22,
        reason=f"用官方文档确认「{topic}」的概念边界，避免把工具用法和模型原理混在一起。",
        matched_goal=goal,
        matched_weak_points=weak_points,
        rank_score=score,
    )


def _oer_candidate(goal: str, weak_points: list[str], topic: str) -> ResourceCandidate:
    query = quote(f"{goal} {topic}")
    return ResourceCandidate(
        resource_id=f"candidate-coursera-{_slug(goal, topic)}",
        type="oer",
        title=f"{topic} 公开课程检索",
        content_preview="公开课程适合补齐系统章节和先修顺序。",
        provider="Coursera",
        source_label="公开课程",
        href=f"https://www.coursera.org/search?query={query}",
        estimated_minutes=35,
        reason=f"当「{topic}」牵涉多个先修点时，用公开课程补齐章节顺序更稳。",
        matched_goal=goal,
        matched_weak_points=weak_points,
        rank_score=0.74,
    )


def _topic(goal: str, weak_points: list[str]) -> str:
    return weak_points[0] if weak_points else goal


def discovery_topic(req: DiscoverResourceRequest) -> str:
    """对外暴露选题口径：优先第一个薄弱点，否则目标本身（与静态候选一致）。"""
    return _topic(req.goal, req.weak_points[:4])


def discovery_query(req: DiscoverResourceRequest) -> str:
    """真实搜索关键词：goal + 选题组合，避免单独薄弱点（如「数学推导」）太泛跑题。"""
    topic = discovery_topic(req)
    if topic and topic != req.goal:
        return f"{req.goal} {topic}"
    return req.goal


def merge_live_videos(
    result: ResourceDiscoveryResult,
    videos: list,
    req: DiscoverResourceRequest,
) -> ResourceDiscoveryResult:
    """用真实 B 站搜索条目替换静态 bilibili 候选；其他 provider 候选保留。

    videos: list[BiliVideo]（鸭子类型：title/bvid/author/duration_minutes）。
    纯函数，无 IO——真实搜索失败时调用方直接跳过本函数走静态候选。
    """
    if not videos:
        return result
    topic = discovery_topic(req)
    weak_points = req.weak_points[:4]
    kept = [item for item in result.items if not item.resource_id.startswith("candidate-bilibili-")]
    live: list[ResourceCandidate] = []
    for index, video in enumerate(videos):
        author = f"UP 主 {video.author} · " if video.author else ""
        live.append(
            ResourceCandidate(
                resource_id=f"candidate-bilibili-{video.bvid}",
                type="external_video",
                title=video.title,
                content_preview=(video.description or f"{author}来自 B 站的真实搜索结果。")[:160],
                provider="Bilibili",
                source_label="B 站视频",
                href=f"https://www.bilibili.com/video/{video.bvid}",
                embed_url=f"https://player.bilibili.com/player.html?bvid={video.bvid}",
                estimated_minutes=video.duration_minutes,
                reason=f"{author}围绕「{topic}」的真实检索结果，先建立直观理解再回到练习。",
                matched_goal=req.goal,
                matched_weak_points=weak_points,
                rank_score=round(0.95 - index * 0.03, 4),
            )
        )
    ranked = sorted([*live, *kept], key=lambda item: item.rank_score, reverse=True)
    return ResourceDiscoveryResult(
        items=ranked[: req.limit],
        query=result.query,
        degraded=[*result.degraded, "bilibili:live"],
    )


def merge_live_docs(
    result: ResourceDiscoveryResult,
    docs: list,
    req: DiscoverResourceRequest,
) -> ResourceDiscoveryResult:
    """用真实 MDN 文档替换静态 official_doc 候选（scikit-learn/PyTorch）；其他保留。

    docs: list[MdnDoc]（鸭子类型：title/url/summary）。纯函数，无 IO。
    """
    if not docs:
        return result
    topic = discovery_topic(req)
    weak_points = req.weak_points[:4]
    kept = [
        item
        for item in result.items
        if not item.resource_id.startswith("candidate-scikit-learn-")
        and not item.resource_id.startswith("candidate-pytorch-")
    ]
    live: list[ResourceCandidate] = []
    for index, doc in enumerate(docs):
        url_slug = doc.url.rstrip("/").rsplit("/", 1)[-1].lower() or str(index)
        live.append(
            ResourceCandidate(
                resource_id=f"candidate-mdn-{url_slug}",
                type="official_doc",
                title=doc.title,
                content_preview=(doc.summary or "MDN Web 官方文档")[:160],
                provider="MDN",
                source_label="官方文档",
                href=doc.url,
                estimated_minutes=18,
                reason=f"MDN 关于「{topic}」的权威文档，用来校准概念边界和标准用法。",
                matched_goal=req.goal,
                matched_weak_points=weak_points,
                rank_score=round(0.88 - index * 0.03, 4),
            )
        )
    ranked = sorted([*live, *kept], key=lambda item: item.rank_score, reverse=True)
    return ResourceDiscoveryResult(
        items=ranked[: req.limit],
        query=result.query,
        degraded=[*result.degraded, "mdn:live"],
    )


def _slug(*parts: str) -> str:
    raw = "-".join(parts).lower()
    chars = [char if char.isalnum() else "-" for char in raw]
    slug = "".join(chars).strip("-")
    return "-".join(part for part in slug.split("-") if part)[:80] or "resource"
