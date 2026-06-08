from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, ValidationError

from reflexlearn.llm_gateway.gateway import Completion
from reflexlearn.eval.schemas import EvalCase, EvalResource, JudgeScore


class EvalLLM(Protocol):
    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        task_type: str,
        schema: type[BaseModel],
        temperature: float,
    ) -> Completion:
        """Subset of LLMGateway used by eval judge."""


class RuleJudge:
    """无 LLM 凭证时的确定性评审器，用于 M5 smoke/e2e 基线。"""

    async def evaluate(
        self,
        *,
        case: EvalCase,
        resource: EvalResource,
        reference: str = "",
    ) -> JudgeScore:
        text = f"{resource.content}\n{reference}"
        correctness = _concept_coverage(text, case.reference_concepts)
        profile_match = _difficulty_score(
            resource.difficulty,
            case.difficulty_min,
            case.difficulty_max,
        )
        completeness = _completion_score(resource.content, case.goal)
        format_quality = _format_score(resource.content, resource.type)
        overall = round(
            correctness * 0.35
            + profile_match * 0.2
            + completeness * 0.3
            + format_quality * 0.15,
            4,
        )
        return JudgeScore(
            correctness=correctness,
            profile_match=profile_match,
            completeness=completeness,
            format_quality=format_quality,
            overall=overall,
            reasoning="rule: concept coverage + difficulty range + content length + format hints",
        )


class LLMJudge:
    """LLM-as-a-judge with deterministic RuleJudge fallback."""

    def __init__(self, llm: EvalLLM, fallback: RuleJudge | None = None):
        self.llm = llm
        self.fallback = fallback or RuleJudge()

    async def evaluate(
        self,
        *,
        case: EvalCase,
        resource: EvalResource,
        reference: str = "",
    ) -> JudgeScore:
        messages = _judge_messages(case, resource, reference)
        try:
            completion = await self.llm.complete(
                messages,
                task_type="judgment",
                schema=JudgeScore,
                temperature=0.0,
            )
            return JudgeScore.model_validate_json(completion.text)
        except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
            return await self.fallback.evaluate(case=case, resource=resource, reference=reference)
        except Exception:
            return await self.fallback.evaluate(case=case, resource=resource, reference=reference)


def _judge_messages(
    case: EvalCase,
    resource: EvalResource,
    reference: str,
) -> list[dict[str, str]]:
    profile = case.profile.model_dump()
    return [
        {
            "role": "system",
            "content": (
                "你是 ReflexLearn 的教育资源评测专家。"
                "请只输出 JSON，字段为 correctness、profile_match、completeness、"
                "format_quality、overall、reasoning，分数范围 0 到 1。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "case_id": case.case_id,
                    "goal": case.goal,
                    "learner_profile": profile,
                    "expected_resource_types": case.expected_resource_types,
                    "reference_concepts": case.reference_concepts,
                    "resource": resource.model_dump(),
                    "reference": reference[:3000],
                },
                ensure_ascii=False,
            ),
        },
    ]


def _concept_coverage(text: str, concepts: list[str]) -> float:
    if not concepts:
        return 0.8
    hits = sum(1 for concept in concepts if concept and concept in text)
    return round(hits / len(concepts), 4)


def _difficulty_score(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 1.0
    distance = min(abs(value - low), abs(value - high))
    return round(max(0.0, 1.0 - distance * 2), 4)


def _completion_score(content: str, goal: str) -> float:
    length_score = min(1.0, len(content.strip()) / 240)
    goal_hits = sum(1 for word in goal.split() if word and word in content)
    goal_score = min(1.0, goal_hits / 2) if goal else 0.8
    return round(max(length_score, goal_score * 0.8), 4)


def _format_score(content: str, resource_type: str) -> float:
    if not content.strip():
        return 0.0
    score = 0.55
    if "#" in content or "：" in content or ":" in content:
        score += 0.2
    if resource_type in {"quiz", "code"} and ("答案" in content or "```" in content):
        score += 0.15
    if len(content) > 120:
        score += 0.1
    return round(min(1.0, score), 4)
