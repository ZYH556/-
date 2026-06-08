from __future__ import annotations

import pytest

from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.offline import OFFLINE_TAG, offline_content
from reflexlearn.skills.video_gen import VideoGenSkill


class _OfflineLLM:
    """模拟无凭证：complete 抛携带 OFFLINE_TAG 的异常，触发离线占位降级。"""

    async def complete(self, messages, **kwargs):
        raise RuntimeError(f"{OFFLINE_TAG}: no api key configured")


class _RealLLM:
    """模拟有凭证：返回一段视频脚本文本，并记录调用参数。"""

    def __init__(self):
        self.calls: list[dict] = []

    async def complete(self, messages, **kwargs):
        from reflexlearn.llm_gateway.gateway import Completion

        self.calls.append({"messages": messages, "kwargs": kwargs})
        return Completion(text="## 视频脚本\n分镜内容足够长以通过基于长度的质量校验规则，并可作为视频生成输入。")


def _ctx() -> SkillContext:
    return SkillContext(user_id="u1", acl={}, task_id="t1")


@pytest.mark.asyncio
async def test_video_gen_offline_falls_back_to_storyboard():
    """无凭证时 video_gen 走 offline 占位，产出含分镜的脚本且足以过质检长度规则。"""
    skill = VideoGenSkill(_OfflineLLM())
    result = await skill.run({"spec": {"concept_ids": ["线性回归"]}, "context": ""}, _ctx())

    assert result.ok
    content = result.data["content"]
    assert "分镜" in content
    assert "线性回归" in content
    assert len(content) > 50
    assert result.data["model_used"] == "offline"


@pytest.mark.asyncio
async def test_video_gen_uses_llm_when_available():
    """有凭证时调用 LLM 生成，task_type 为 generation。"""
    llm = _RealLLM()
    skill = VideoGenSkill(llm)
    result = await skill.run(
        {"spec": {"concept_ids": ["线性回归"], "difficulty": 0.5}, "context": "ctx"}, _ctx()
    )

    assert result.ok
    assert result.data["content"].startswith("## 视频脚本")
    assert llm.calls[0]["kwargs"]["task_type"] == "generation"


def test_offline_content_video_is_storyboard():
    """offline_content('video') 产出带分镜与旁白的视频脚本，围绕给定概念生成。"""
    content = offline_content("video", {"concept_ids": ["梯度下降"]})
    assert "分镜" in content
    assert "梯度下降" in content
    assert "旁白" in content
    assert len(content) > 50
