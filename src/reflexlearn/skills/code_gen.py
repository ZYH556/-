from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class CodeGenSkill:
    name = "code_gen"
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
                    "你是机器学习代码案例生成器。"
                    "生成可运行 Python 示例，优先使用 numpy 或 sklearn。"
                    "必须包含代码、运行说明、关键输出解释和学习要点。"
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
            # try 块只包 LLM 调用：无 key / key 失效(403) / 网络故障一律视为
            # LLM 不可用，统一降级离线占位（与无 key 行为一致，绝不报错中断）。
            duration = int((time.time() - start) * 1000)
            from reflexlearn.skills.offline import log_llm_fallback, offline_content

            log_llm_fallback(self.name, e)
            return SkillResult(
                ok=True,
                data={
                    "content": offline_content("code", spec),
                    "model_used": "offline",
                    "degraded_from": type(e).__name__,
                },
                duration_ms=duration,
            )
