from __future__ import annotations

import json

from pydantic import ValidationError

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.state import AgentState
from reflexlearn.orchestration.schemas import LearnerProfile
from reflexlearn.memory.trim import trim_context, TrimConfig
from reflexlearn.memory.recursive_summary import get_context


async def profile_node(state: AgentState) -> dict:
    goal = state.get("learning_goal", "")
    llm = state.get("_llm")

    profile = None
    if get_settings().enable_llm_profile:
        profile = await _extract_with_llm(llm, state)
    if profile is None:
        profile = _fallback_profile(goal, state.get("learner_profile", {}))

    return {"learner_profile": profile.model_dump(), "iteration": state.get("iteration", 0) + 1}


async def _extract_with_llm(llm, state: AgentState) -> LearnerProfile | None:
    if llm is None:
        return None

    # L1 上下文工程：按语义重要性 + summary buffer 裁剪历史，替代朴素 messages[-8:]，
    # 兼容多轮长对话；结果仅供本次 LLM 调用，绝不回写 state["messages"]（add_messages reducer）。
    summary_ctx = get_context(state.get("summary_layers", []))
    trimmed = trim_context(state.get("messages", []), summary_ctx, TrimConfig.from_settings())

    messages = [
        {
            "role": "system",
            "content": (
                "你是学习者画像抽取 Agent。"
                "请根据对话历史抽取 LearnerProfile。"
                "knowledge_base 的值必须是 0 到 1 的掌握度；"
                "cognitive_style 只能是 visual、verbal、active、reflective。"
                "只输出 JSON。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "learning_goal": state.get("learning_goal", ""),
                    "messages": trimmed,
                    "existing_profile": state.get("learner_profile", {}),
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        completion = await llm.complete(
            messages,
            task_type="profiling",
            schema=LearnerProfile,
            temperature=0.0,
        )
        return LearnerProfile.model_validate_json(completion.text)
    except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
        return None
    except Exception:
        return None


def _fallback_profile(goal: str, existing: dict | None = None) -> LearnerProfile:
    fallback = LearnerProfile(
        knowledge_base={"python": 0.7, "statistics": 0.4, "machine_learning": 0.3},
        cognitive_style="active",
        goal=goal,
        weak_points=["数学推导", "概率论基础"],
        preferences={"language": "zh", "prefer_code_examples": True},
        progress=0.0,
    )
    if not existing:
        return fallback
    try:
        old = LearnerProfile.model_validate(existing)
    except ValidationError:
        return fallback

    knowledge_base = {**fallback.knowledge_base, **old.knowledge_base}
    weak_points = list(dict.fromkeys([*old.weak_points, *fallback.weak_points]))
    preferences = {**fallback.preferences, **old.preferences}
    return LearnerProfile(
        knowledge_base=knowledge_base,
        cognitive_style=old.cognitive_style or fallback.cognitive_style,
        goal=goal or old.goal,
        weak_points=weak_points,
        preferences=preferences,
        progress=max(old.progress, fallback.progress),
    )
