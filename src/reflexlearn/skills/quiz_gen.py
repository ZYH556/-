from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class QuizGenSkill:
    name = "quiz_gen"
    max_calls_per_task = 3
    cache_ttl = None

    def __init__(self, llm: LLMGateway):
        self.llm = llm

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult:
        start = time.time()
        spec = inp.get("spec", {})
        context = inp.get("context", "")
        concept = ", ".join(spec.get("concept_ids", ["未指定概念"]))
        issues = spec.get("previous_issues", [])

        messages = [
            {
                "role": "system",
                "content": (
                    "你是机器学习练习题生成器。"
                    "生成 3 道题，必须包含题干、难度标签、答案和解析。"
                    "使用 Markdown，题目要覆盖概念理解和应用。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"知识点：{concept}\n"
                    f"难度：{spec.get('difficulty', 0.5)}\n"
                    f"学习风格：{spec.get('style_hint', '')}\n"
                    f"参考上下文：{context[:1000] if context else '无'}\n"
                    f"需要修复的问题：{issues if issues else '无'}"
                ),
            },
        ]

        try:
            completion = await self.llm.complete(messages, task_type="generation")
            duration = int((time.time() - start) * 1000)
            return SkillResult(
                ok=True,
                data={"content": completion.text, "model_used": completion.model_used},
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            from reflexlearn.skills.offline import OFFLINE_TAG, offline_content

            if OFFLINE_TAG in str(e):
                return SkillResult(
                    ok=True,
                    data={"content": offline_content("quiz", spec), "model_used": "offline"},
                    duration_ms=duration,
                )
            return SkillResult(ok=False, error_type=str(type(e).__name__), duration_ms=duration)
