from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from reflexlearn.learning.mistakes import MistakeItem
from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.code_gen import CodeGenSkill
from reflexlearn.skills.doc_gen import DocGenSkill
from reflexlearn.skills.path_plan import PathPlanSkill
from reflexlearn.skills.quiz_gen import QuizGenSkill

MistakeCategory = Literal["概念不清", "步骤遗漏", "公式/代码错误", "审题偏差", "记忆遗忘"]


class MistakeReflection(BaseModel):
    mistake_id: str
    category: MistakeCategory
    cause: str
    evidence: list[str] = Field(default_factory=list)
    remedial_goal: str
    difficulty: float = 0.5


class MistakePlan(BaseModel):
    mistake_id: str
    remedial_goal: str
    steps: list[dict] = Field(default_factory=list)
    summary: str = ""
    strategy: str = ""


class MistakeResource(BaseModel):
    resource_id: str
    mistake_id: str
    type: str
    title: str
    content: str


class MistakeResourcePack(BaseModel):
    mistake_id: str
    resources: list[MistakeResource] = Field(default_factory=list)


class ReviewPatch(BaseModel):
    review_status: Literal["open", "reviewing", "reviewed"] = "reviewed"


class OfflineLLM:
    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        raise RuntimeError("no_api_key")


def reflect_mistake(item: MistakeItem) -> MistakeReflection:
    text = f"{item.question}\n{item.answer}\n{item.expected}".lower()
    concept = _concept(item)
    if any(key in text for key in ["代码", "python", "梯度", "公式", "损失", "报错"]):
        category: MistakeCategory = "公式/代码错误"
    elif any(key in text for key in ["忘", "记不住", "混淆"]):
        category = "记忆遗忘"
    elif any(key in text for key in ["为什么", "原理", "概念", "定义"]):
        category = "概念不清"
    elif len(item.answer.strip()) < max(8, len(item.expected.strip()) // 3):
        category = "步骤遗漏"
    else:
        category = "审题偏差"
    cause = _cause_for(category, concept)
    return MistakeReflection(
        mistake_id=item.mistake_id,
        category=category,
        cause=cause,
        evidence=[
            f"你的答案：{item.answer[:120]}",
            f"参考要点：{item.expected[:120]}",
        ],
        remedial_goal=f"围绕「{concept}」补齐 {category} 对应的理解与练习。",
        difficulty=_difficulty_for(category),
    )


async def build_remedial_plan(item: MistakeItem, reflection: MistakeReflection | None = None) -> MistakePlan:
    reflection = reflection or reflect_mistake(item)
    concept = _concept(item)
    resources = [
        _plan_resource("review-doc", "doc", concept, reflection.difficulty),
        _plan_resource("worked-example", "mindmap", concept, min(1.0, reflection.difficulty + 0.05)),
        _plan_resource("target-quiz", "quiz", concept, min(1.0, reflection.difficulty + 0.1)),
        _plan_resource("spaced-review", "reading", concept, min(1.0, reflection.difficulty + 0.15)),
    ]
    if _needs_code(item, reflection):
        resources.insert(2, _plan_resource("repair-code", "code", concept, min(1.0, reflection.difficulty + 0.1)))
    skill = PathPlanSkill(OfflineLLM())
    result = await skill.run(
        {"resources": resources[:5], "profile": {"weak_points": [concept]}, "goal": reflection.remedial_goal},
        _ctx(item, "mistake-plan"),
    )
    data = result.data or {}
    return MistakePlan(
        mistake_id=item.mistake_id,
        remedial_goal=reflection.remedial_goal,
        steps=(data.get("path") or [])[:5],
        summary=data.get("summary") or "",
        strategy=data.get("strategy") or "规则补救计划",
    )


async def generate_targeted_resources(
    item: MistakeItem,
    reflection: MistakeReflection | None = None,
) -> MistakeResourcePack:
    reflection = reflection or reflect_mistake(item)
    concept = _concept(item)
    spec = {
        "concept_ids": [concept],
        "difficulty": reflection.difficulty,
        "previous_issues": [reflection.category, reflection.cause],
        "style_hint": "错题补救，先解释错因，再给反例和练习。",
    }
    skills: list[tuple[str, object]] = [
        ("doc", DocGenSkill(OfflineLLM())),
        ("quiz", QuizGenSkill(OfflineLLM())),
    ]
    if _needs_code(item, reflection):
        skills.append(("code", CodeGenSkill(OfflineLLM())))

    resources: list[MistakeResource] = []
    for kind, skill in skills:
        result = await skill.run({"spec": spec, "context": reflection.cause}, _ctx(item, f"mistake-{kind}"))
        content = (result.data or {}).get("content", "") if result.ok else f"{concept} 针对性资源生成降级。"
        resources.append(
            MistakeResource(
                resource_id=f"mistake:{item.mistake_id}:{kind}:{uuid4().hex[:8]}",
                mistake_id=item.mistake_id,
                type=kind,
                title=f"{concept} · {kind} 补救资源",
                content=content,
            )
        )
    return MistakeResourcePack(mistake_id=item.mistake_id, resources=resources)


def _ctx(item: MistakeItem, task_id: str) -> SkillContext:
    return SkillContext(
        user_id=item.user_id,
        acl={"user_id": item.user_id, "tenant_id": item.tenant_id, "visibility": ["private"]},
        task_id=task_id,
    )


def _plan_resource(task_id: str, rtype: str, concept: str, difficulty: float) -> dict:
    return {
        "task_id": task_id,
        "resource_type": rtype,
        "concept": concept,
        "difficulty": difficulty,
    }


def _needs_code(item: MistakeItem, reflection: MistakeReflection) -> bool:
    text = f"{item.question}\n{item.answer}\n{item.expected}".lower()
    return reflection.category == "公式/代码错误" and any(key in text for key in ["代码", "python", "梯度"])


def _concept(item: MistakeItem) -> str:
    return item.concept.strip() or "错题相关概念"


def _difficulty_for(category: MistakeCategory) -> float:
    return {
        "概念不清": 0.35,
        "步骤遗漏": 0.45,
        "公式/代码错误": 0.6,
        "审题偏差": 0.4,
        "记忆遗忘": 0.3,
    }[category]


def _cause_for(category: MistakeCategory, concept: str) -> str:
    return {
        "概念不清": f"对「{concept}」的定义、适用条件或核心直觉掌握不稳。",
        "步骤遗漏": f"解题链路中缺少关键步骤，导致「{concept}」应用不完整。",
        "公式/代码错误": f"在「{concept}」的公式推导、符号方向或代码实现上出现偏差。",
        "审题偏差": f"题目要求与作答重点不一致，需要先校准「{concept}」的考查点。",
        "记忆遗忘": f"相关知识曾学过但提取失败，需要对「{concept}」做间隔复习。",
    }[category]
