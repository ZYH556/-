from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ResourceType = Literal[
    "external_video",
    "official_doc",
    "oer",
    "ai_document",
    "quiz",
    "user_upload",
]


class DemoSpace(BaseModel):
    space_id: str
    user_id: str
    tenant_id: str
    title: str
    course: str = ""
    status: str = "active"
    progress: float = 0.0


class DemoResource(BaseModel):
    resource_id: str
    user_id: str
    tenant_id: str
    space_id: str
    type: ResourceType
    title: str
    provider: str
    source_label: str
    estimated_minutes: int
    reason: str
    href: str
    embed_url: str = ""
    usage_mode: str = "personal"
    source_policy: str = "owned_or_generated"
    concept: str = ""
    content: str = ""


class DemoMistake(BaseModel):
    mistake_id: str
    user_id: str
    tenant_id: str
    question: str
    answer: str
    expected: str
    concept: str
    status: str = "open"
    source_resource_id: str = ""


class DemoProfile(BaseModel):
    user_id: str
    tenant_id: str
    goal: str
    weak_points: list[str] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)
    progress: float = 0.0
    cognitive_style: str = "active"
    knowledge_base: dict[str, float] = Field(default_factory=dict)


class DemoSeed(BaseModel):
    spaces: list[DemoSpace] = Field(default_factory=list)
    resources: list[DemoResource] = Field(default_factory=list)
    mistakes: list[DemoMistake] = Field(default_factory=list)
    profiles: list[DemoProfile] = Field(default_factory=list)


def build_demo_seed(user_id: str, tenant_id: str) -> DemoSeed:
    spaces = _spaces(user_id, tenant_id)
    return DemoSeed(
        spaces=spaces,
        resources=_resources(user_id, tenant_id, spaces),
        mistakes=_mistakes(user_id, tenant_id),
        profiles=_profiles(user_id, tenant_id),
    )


def _spaces(user_id: str, tenant_id: str) -> list[DemoSpace]:
    items = [
        ("seed-space-ml", "机器学习基础强化", "机器学习", 0.62),
        ("seed-space-frontend", "前端工程能力提升", "前端工程", 0.44),
        ("seed-space-math", "高等数学错题复盘", "高等数学", 0.37),
        ("seed-space-python", "Python 数据分析入门", "数据分析", 0.52),
        ("seed-space-ai-product", "AI 应用项目实践", "AI 应用", 0.28),
    ]
    return [
        DemoSpace(
            space_id=space_id,
            user_id=user_id,
            tenant_id=tenant_id,
            title=title,
            course=course,
            progress=progress,
        )
        for space_id, title, course, progress in items
    ]


def _resources(user_id: str, tenant_id: str, spaces: list[DemoSpace]) -> list[DemoResource]:
    concepts = [
        "损失函数",
        "梯度下降",
        "学习率",
        "过拟合",
        "React 状态模型",
        "异步请求",
        "链式求导",
        "矩阵乘法",
        "Pandas 数据清洗",
        "项目拆解",
    ]
    templates = [
        ("external_video", "Bilibili", "B 站视频"),
        ("official_doc", "scikit-learn", "官方资料"),
        ("oer", "MIT OpenCourseWare", "开放课程"),
        ("ai_document", "ReflexLearn AI 导师", "AI 讲解文档"),
        ("quiz", "ReflexLearn 练习生成", "针对练习"),
        ("user_upload", "个人资料", "个人资料"),
    ]
    items: list[DemoResource] = []
    for idx in range(24):
        concept = concepts[idx % len(concepts)]
        kind, provider, label = templates[idx % len(templates)]
        space = spaces[idx % len(spaces)]
        items.append(
            _resource(
                idx=idx + 1,
                user_id=user_id,
                tenant_id=tenant_id,
                space_id=space.space_id,
                kind=kind,  # type: ignore[arg-type]
                provider=provider,
                label=label,
                concept=concept,
            )
        )
    return items


def _resource(
    *,
    idx: int,
    user_id: str,
    tenant_id: str,
    space_id: str,
    kind: ResourceType,
    provider: str,
    label: str,
    concept: str,
) -> DemoResource:
    title = _resource_title(kind, concept)
    is_video = kind == "external_video"
    bvid = "BV1lossGuide" if concept == "损失函数" else f"BV1learn{idx:02d}"
    return DemoResource(
        resource_id=f"seed-resource-{idx:02d}",
        user_id=user_id,
        tenant_id=tenant_id,
        space_id=space_id,
        type=kind,
        title=title,
        provider=provider,
        source_label=label,
        estimated_minutes=8 + idx % 18,
        reason=f"围绕“{concept}”补齐理解、练习和迁移应用。",
        href=_resource_href(kind, concept, bvid),
        embed_url=f"https://player.bilibili.com/player.html?bvid={bvid}" if is_video else "",
        usage_mode="metadata_only" if is_video else "personal",
        source_policy="embed_or_redirect_only" if is_video else "owned_or_generated",
        concept=concept,
        content=f"{title}：用于支持“{concept}”的学习与复盘。",
    )


def _resource_title(kind: ResourceType, concept: str) -> str:
    titles = {
        "external_video": f"{concept}视频讲解",
        "official_doc": f"{concept}官方参考",
        "oer": f"{concept}开放课程笔记",
        "ai_document": f"{concept}个性化讲解",
        "quiz": f"{concept}五题短练",
        "user_upload": f"{concept}课堂资料整理",
    }
    return titles[kind]


def _resource_href(kind: ResourceType, concept: str, bvid: str) -> str:
    if kind == "external_video":
        if concept == "损失函数":
            return f"https://www.bilibili.com/video/{bvid}"
        return f"https://search.bilibili.com/all?keyword={concept}"
    if kind == "official_doc":
        return "https://scikit-learn.org/stable/modules/linear_model.html"
    if kind == "oer":
        return "https://ocw.mit.edu/"
    if kind == "quiz":
        return "/chat"
    return "/resources"


def _mistakes(user_id: str, tenant_id: str) -> list[DemoMistake]:
    concepts = [
        "损失函数",
        "梯度方向",
        "学习率",
        "过拟合",
        "链式求导",
        "闭包",
        "异步状态",
        "矩阵乘法",
        "特征缩放",
        "模型评估",
    ]
    return [
        DemoMistake(
            mistake_id=f"seed-mistake-{idx:02d}",
            user_id=user_id,
            tenant_id=tenant_id,
            question=f"{concept}相关练习",
            answer="解答中缺少关键条件或概念边界。",
            expected="需要说明定义、适用条件和推导步骤。",
            concept=concept,
            status="open" if idx <= 6 else "reviewing",
        )
        for idx, concept in enumerate(concepts, start=1)
    ]


def _profiles(user_id: str, tenant_id: str) -> list[DemoProfile]:
    return [
        DemoProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            goal="掌握线性回归与梯度下降",
            weak_points=["损失函数", "梯度方向", "学习率"],
            preferences={"resource_mix": "视频讲解 + 五题短练习"},
            progress=0.62,
            knowledge_base={"线性回归": 0.68, "梯度下降": 0.42},
        ),
        DemoProfile(
            user_id="student-frontend",
            tenant_id=tenant_id,
            goal="准备前端工程师面试",
            weak_points=["React 状态模型", "浏览器渲染", "异步请求"],
            preferences={"resource_mix": "代码案例 + 面试题"},
            progress=0.44,
            cognitive_style="case_first",
        ),
        DemoProfile(
            user_id="student-math",
            tenant_id=tenant_id,
            goal="复盘高等数学错题",
            weak_points=["链式求导", "极限变形", "积分换元"],
            preferences={"resource_mix": "公式推导 + 错题复盘"},
            progress=0.37,
            cognitive_style="derivation_first",
        ),
    ]
