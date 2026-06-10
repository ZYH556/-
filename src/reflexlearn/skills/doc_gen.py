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
        issues = spec.get("previous_issues", [])
        fix_notes = "；".join(str(i) for i in issues if i)

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
                    f"需修复点：{fix_notes or '无'}\n"
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
            # try 块只包 LLM 调用：无 key / key 失效(403) / 网络故障一律视为
            # LLM 不可用，统一降级离线占位（与无 key 行为一致，绝不报错中断）。
            duration = int((time.time() - start) * 1000)
            from reflexlearn.skills.offline import log_llm_fallback, offline_content

            log_llm_fallback(self.name, e)
            return SkillResult(
                ok=True,
                data={
                    "content": offline_content("doc", spec),
                    "model_used": "offline",
                    "degraded_from": type(e).__name__,
                },
                duration_ms=duration,
            )
