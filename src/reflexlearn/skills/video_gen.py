from __future__ import annotations

import time

from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.skills.base import SkillContext, SkillResult


class VideoGenSkill:
    """多模态视频资源生成 Skill。

    产出可直接用于视频生成的分镜脚本（storyboard）——含时长 / 风格、多个分镜的
    画面描述与旁白文案。当前阶段（M2）以脚本形式呈现，作为 M4 接入视频生成服务
    （如 SeeDance）的天然输入；离线无凭证时走 offline_content 占位，保证端到端可演示。
    """

    name = "video_gen"
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
                    "你是多模态教学视频的分镜脚本设计师。"
                    "围绕给定知识点产出一段可直接用于视频生成的分镜脚本（storyboard）："
                    "开头标注总时长与风格，随后给出 4-6 个分镜，每个分镜包含时间区间、"
                    "画面描述与旁白文案。使用 Markdown，结构清晰，便于后续渲染为讲解视频或动画。"
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
                    data={"content": offline_content("video", spec), "model_used": "offline"},
                    duration_ms=duration,
                )
            return SkillResult(ok=False, error_type=str(type(e).__name__), duration_ms=duration)
