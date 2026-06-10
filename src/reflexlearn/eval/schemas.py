from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class EvalProfile(BaseModel):
    knowledge_base: dict[str, float] = Field(default_factory=dict)
    cognitive_style: Literal["visual", "verbal", "active", "reflective"] = "active"
    weak_points: list[str] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)
    progress: float = Field(default=0.0, ge=0, le=1)


class EvalCase(BaseModel):
    case_id: str
    goal: str
    profile: EvalProfile = Field(default_factory=EvalProfile)
    expected_resource_types: list[str] = Field(default_factory=list)
    reference_concepts: list[str] = Field(default_factory=list)
    difficulty_min: float = Field(default=0.0, ge=0, le=1)
    difficulty_max: float = Field(default=1.0, ge=0, le=1)
    tags: list[str] = Field(default_factory=list)


class EvalResource(BaseModel):
    task_id: str
    type: str
    content: str
    difficulty: float = Field(default=0.5, ge=0, le=1)


class JudgeScore(BaseModel):
    correctness: float = Field(default=0.0, ge=0, le=1)
    profile_match: float = Field(default=0.0, ge=0, le=1)
    completeness: float = Field(default=0.0, ge=0, le=1)
    format_quality: float = Field(default=0.0, ge=0, le=1)
    overall: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""


class EvalTraceEvent(BaseModel):
    sequence: int
    node: str
    elapsed_ms: int = 0
    keys: list[str] = Field(default_factory=list)
    summary: str = ""


class EvalResult(BaseModel):
    case_id: str
    strategy: str
    task_completed: bool
    resource_types_generated: list[str] = Field(default_factory=list)
    resource_coverage: float = Field(default=0.0, ge=0, le=1)
    resource_scores: list[JudgeScore] = Field(default_factory=list)
    latency_ms: int = 0
    error: str = ""
    last_event: str = ""
    event_trace: list[EvalTraceEvent] = Field(default_factory=list)


class EvalReport(BaseModel):
    strategy: str
    total_cases: int
    task_completion_rate: float = 0.0
    avg_resource_coverage: float = 0.0
    avg_correctness: float = 0.0
    avg_profile_match: float = 0.0
    avg_completeness: float = 0.0
    avg_format_quality: float = 0.0
    avg_overall: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: list[EvalResult] = Field(default_factory=list)
