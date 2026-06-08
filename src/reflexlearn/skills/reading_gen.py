from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class ReadingGenSkill:
    name = "reading_gen"
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
                    "你是机器学习拓展阅读推荐器。"
                    "围绕给定知识点推荐 3-5 项进阶阅读材料（论文 / 书籍章节 / 优质博客 / 官方文档）。"
                    "每项包含标题、类型、一句话推荐理由和阅读难度。使用 Markdown 列表，由易到难排序。"
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
                    data={"content": offline_content("reading", spec), "model_used": "offline"},
                    duration_ms=duration,
                )
            return SkillResult(ok=False, error_type=str(type(e).__name__), duration_ms=duration)
