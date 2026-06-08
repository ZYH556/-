from __future__ import annotations

import json
import time

from pydantic import ValidationError

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.orchestration.schemas import VerifyResult
from reflexlearn.skills.base import SkillContext, SkillResult


class QualityCheckSkill:
    name = "quality_check"
    max_calls_per_task = 4
    cache_ttl = None

    def __init__(self, llm: LLMGateway | None = None):
        self.llm = llm

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult:
        start = time.time()
        result = await self._judge_with_llm(inp)
        if result is None:
            result = self._rule_check(inp.get("content", ""))

        duration = int((time.time() - start) * 1000)
        return SkillResult(
            ok=True,
            data=result.model_dump(),
            duration_ms=duration,
        )

    async def _judge_with_llm(self, inp: dict) -> VerifyResult | None:
        if self.llm is None:
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    "你是学习资源质量评审器。"
                    "请从格式完整性、画像匹配度、知识准确性三个维度评分。"
                    "只输出 JSON，字段为 passed、layer_failed、score、issues、fixable。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "resource": inp.get("content", ""),
                        "spec": inp.get("spec", {}),
                        "learner_profile": inp.get("profile", {}),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        try:
            completion = await self.llm.complete(
                messages,
                task_type="verification",
                schema=VerifyResult,
                temperature=0.0,
            )
            return VerifyResult.model_validate_json(completion.text)
        except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
            return None
        except Exception:
            return None

    def _rule_check(self, content: str) -> VerifyResult:
        passed = len(content) > 50
        return VerifyResult(
            passed=passed,
            layer_failed="none" if passed else "format",
            score=0.8 if passed else 0.3,
            issues=[] if passed else ["内容过短"],
            fixable=True,
        )
