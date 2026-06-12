"""微型智能辅导：全局浮窗的即时答疑端点。

与 /chat 的完整多智能体链路不同，/tutor/ask 是单次轻量 LLM 调用：
带学习画像上下文直答，追求秒级响应；无凭证/外呼失败降级为
离线引导占位，绝不报错中断。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from reflexlearn.api.deps import get_current_user
from reflexlearn.common.auth import CurrentUser
from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.memory import session_store
from reflexlearn.safety import SafetyGateway

logger = logging.getLogger(__name__)
router = APIRouter()

_gateway: LLMGateway | None = None


def _get_gateway() -> LLMGateway:
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


def set_gateway_for_tests(gateway) -> None:
    global _gateway
    _gateway = gateway


def reset_gateway_for_tests() -> None:
    global _gateway
    _gateway = None


class TutorAskRequest(BaseModel):
    question: str
    context_hint: str = ""


class TutorReply(BaseModel):
    answer: str
    degraded: bool = False
    blocked: bool = False
    reasons: list[str] = []


_OFFLINE_ANSWER = (
    "（离线辅导占位）当前 AI 服务暂不可用，先给你一个通用建议：\n"
    "1. 把问题拆成「概念定义 → 典型例子 → 易错点」三步自查；\n"
    "2. 如果是题目卡住，回到对应章节的讲解文档重读相关小节；\n"
    "3. 可以把这道题录入错题本，系统会在服务恢复后生成针对性补救资源。"
)


@router.post("/tutor/ask")
async def tutor_ask(req: TutorAskRequest, user: CurrentUser = Depends(get_current_user)):
    decision = SafetyGateway().check_input(req.question)
    if not decision.allowed:
        return TutorReply(answer="", blocked=True, reasons=decision.reasons)

    profile = await session_store.load_profile(user.user_id, tenant_id=user.tenant_id)
    system = (
        "你是 ReflexLearn 的 1 对 1 学习导师，负责即时答疑。"
        "回答要求：直接给出解释，必要时给一个小例子；控制在 300 字以内；"
        "如果学生画像里有薄弱点与当前问题相关，结尾给一句针对性的复习建议。"
    )
    context_parts: list[str] = []
    if profile:
        weak = "、".join(profile.get("weak_points", [])[:4])
        if weak:
            context_parts.append(f"学生薄弱点：{weak}")
        if profile.get("goal"):
            context_parts.append(f"学习目标：{profile['goal']}")
    if req.context_hint:
        context_parts.append(f"提问场景：{req.context_hint[:200]}")
    user_content = req.question
    if context_parts:
        user_content = "（上下文：" + "；".join(context_parts) + "）\n\n" + req.question

    try:
        completion = await _get_gateway().complete(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            task_type="tutoring",
            temperature=0.3,
        )
        answer = SafetyGateway().check_output(completion.text).redacted_text
        return TutorReply(answer=answer)
    except Exception as exc:
        logger.info("tutor ask degraded: %s", exc)
        return TutorReply(answer=_OFFLINE_ANSWER, degraded=True)
