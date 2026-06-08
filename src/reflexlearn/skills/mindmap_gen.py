from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class MindmapGenSkill:
    name = "mindmap_gen"
    max_calls_per_task = 2
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
                    "你是机器学习思维导图生成器。"
                    "输出 Mermaid mindmap，包含核心概念、公式直觉、步骤、常见误区和练习方向。"
                    "内容要简洁，节点层级清晰。"
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
                    data={"content": offline_content("mindmap", spec), "model_used": "offline"},
                    duration_ms=duration,
                )
            return SkillResult(ok=False, error_type=str(type(e).__name__), duration_ms=duration)
