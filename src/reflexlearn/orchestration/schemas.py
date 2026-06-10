from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LearnerProfile(BaseModel):
    knowledge_base: dict[str, float] = Field(default_factory=dict)
    cognitive_style: Literal["visual", "verbal", "active", "reflective"] = "active"
    goal: str = ""
    weak_points: list[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    progress: float = 0.0


class ResourceSpec(BaseModel):
    type: Literal["doc", "mindmap", "quiz", "reading", "code", "video"]
    concept_ids: list[str] = Field(default_factory=list)
    difficulty: float = Field(default=0.5, ge=0, le=1)
    style_hint: str = ""
    constraints: list[str] = Field(default_factory=list)


class VerifyResult(BaseModel):
    passed: bool
    layer_failed: Literal["none", "format", "profile_match", "knowledge"] = "none"
    score: float = Field(default=0.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    fixable: bool = True


class Reflection(BaseModel):
    task_type: str
    failure_type: str
    cause: str
    fix_strategy: str
    success: bool = False


class MetaReview(BaseModel):
    score: float = Field(default=1.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    refine_hint: str = ""
    suggested_skill: str = ""


class DebateRound(BaseModel):
    round: int
    positions: list[dict] = Field(default_factory=list)


class DebateResult(BaseModel):
    winner_position: str
    reasoning: str
    confidence: float = Field(default=0.0, ge=0, le=1)


class ACLScope(BaseModel):
    user_id: str
    tenant_id: str = "default"
    course_ids: list[str] = Field(default_factory=list)
    visibility: list[str] = Field(default_factory=lambda: ["public", "course", "private"])


class LearningPathStep(BaseModel):
    sequence: int
    task_id: str
    # 不用 Literal：debate 结论(type="debate")等非 ResourceType 资源也要能进路径
    resource_type: str
    concept: str = ""
    objective: str = ""       # 这一步要达成的学习目标
    rationale: str = ""       # 为何排在这个位置（可解释，呼应「学习画像可解释」）
    difficulty: float = Field(default=0.5, ge=0, le=1)
    depends_on: list[str] = Field(default_factory=list)  # 前置步骤 task_id；图谱依赖预留，本轮启发式


class LearningPathPlan(BaseModel):
    steps: list[LearningPathStep] = Field(default_factory=list)
    summary: str = ""         # 路径总览
    strategy: str = ""        # 排序依据说明
