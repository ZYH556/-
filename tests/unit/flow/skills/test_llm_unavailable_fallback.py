"""LLM 凭证失效 / 网络故障时，生成类 Skill 必须与「无 key」行为一致：降级离线占位。

背景：2026-06-10 活体演示中中转站返回 403 GROUP_DISABLED（key 分组停用），
旧实现只对异常消息含 OFFLINE_TAG（no_api_key）的情况走离线占位，
HTTPStatusError 直接 ok=False → critic 全拒 → 多轮重规划 → 0 资源收场，
违反降级铁律「绝不报错中断、绝不假装成功」。
这些 Skill 的 try 块只包 LLM 调用，因此任何异常都意味着本次 LLM 不可用，
统一降级离线占位（model_used=offline + degraded_from 标注）。
"""

from __future__ import annotations

import httpx
import pytest

from reflexlearn.skills.base import SkillContext
from reflexlearn.skills.code_gen import CodeGenSkill
from reflexlearn.skills.doc_gen import DocGenSkill
from reflexlearn.skills.mindmap_gen import MindmapGenSkill
from reflexlearn.skills.quiz_gen import QuizGenSkill
from reflexlearn.skills.reading_gen import ReadingGenSkill
from reflexlearn.skills.video_gen import VideoGenSkill


class _ForbiddenLLM:
    """模拟中转站 key 分组停用：complete 抛 httpx.HTTPStatusError(403)。"""

    async def complete(self, messages, **kwargs):
        request = httpx.Request("POST", "https://relay.example.com/responses")
        response = httpx.Response(403, request=request)
        raise httpx.HTTPStatusError(
            "Client error '403 Forbidden'", request=request, response=response
        )


class _ConnectErrorLLM:
    """模拟网络不可达：complete 抛 httpx.ConnectError。"""

    async def complete(self, messages, **kwargs):
        raise httpx.ConnectError("connection refused")


def _ctx() -> SkillContext:
    return SkillContext(user_id="u1", acl={}, task_id="t1")


_SKILLS = [
    (DocGenSkill, "doc"),
    (QuizGenSkill, "quiz"),
    (MindmapGenSkill, "mindmap"),
    (CodeGenSkill, "code"),
    (ReadingGenSkill, "reading"),
    (VideoGenSkill, "video"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("skill_cls,kind", _SKILLS)
async def test_http_403_falls_back_to_offline_content(skill_cls, kind):
    """key 失效（403）与无 key 行为一致：离线占位、可过质检长度规则。"""
    skill = skill_cls(_ForbiddenLLM())
    result = await skill.run({"spec": {"concept_ids": ["线性回归"]}, "context": ""}, _ctx())

    assert result.ok, f"{kind} 在 LLM 403 时应降级离线占位而非失败"
    assert result.data["model_used"] == "offline"
    assert len(result.data["content"]) > 50
    assert result.data["degraded_from"] == "HTTPStatusError"


@pytest.mark.asyncio
async def test_connect_error_falls_back_to_offline_content():
    """网络不可达同样降级离线占位（以 doc 为代表）。"""
    skill = DocGenSkill(_ConnectErrorLLM())
    result = await skill.run({"spec": {"concept_ids": ["梯度下降"]}, "context": ""}, _ctx())

    assert result.ok
    assert result.data["model_used"] == "offline"
    assert "梯度下降" in result.data["content"]
    assert result.data["degraded_from"] == "ConnectError"
