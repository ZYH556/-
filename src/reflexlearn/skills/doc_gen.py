from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class DocGenSkill:
    name = "doc_gen"
    max_calls_per_task = 3
    cache_ttl = None

    def __init__(self, llm: LLMGateway):
        self.llm = llm

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult:
        start = time.time()
        spec = inp.get("spec", {})
        context = inp.get("context", "")
        concept = ", ".join(spec.get("concept_ids", ["未指定概念"]))
        difficulty = spec.get("difficulty", 0.5)

        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个专业的机器学习教学内容生成器。"
                    "根据给定的知识点和难度等级，生成一份结构化的学习文档。"
                    "使用 Markdown 格式，包含标题、概念解释、示例和要点总结。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"请为以下知识点生成学习文档：\n"
                    f"知识点：{concept}\n"
                    f"难度等级：{difficulty}\n"
                    f"参考上下文：{context[:1000] if context else '无'}\n"
                    f"要求：控制在 500 字以内，结构清晰。"
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
                    data={"content": offline_content("doc", spec), "model_used": "offline"},
                    duration_ms=duration,
                )
            return SkillResult(ok=False, error_type=str(type(e).__name__), duration_ms=duration)
