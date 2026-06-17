from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult
from reflexlearn.skills.streaming import generate_text


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
            text, model_used = await generate_text(
                self.llm, messages, task_type="generation", sink=getattr(ctx, "delta_sink", None)
            )
            duration = int((time.time() - start) * 1000)
            return SkillResult(
                ok=True,
                data={"content": text, "model_used": model_used},
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
                    "content": offline_content("reading", spec),
                    "model_used": "offline",
                    "degraded_from": type(e).__name__,
                },
                duration_ms=duration,
            )
