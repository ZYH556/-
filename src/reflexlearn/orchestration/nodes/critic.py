from __future__ import annotations

import json

from pydantic import ValidationError

from reflexlearn.common.db import get_pg_pool, get_qdrant
from reflexlearn.orchestration.schemas import Reflection
from reflexlearn.orchestration.state import AgentState
from reflexlearn.memory.reflexion import write_reflection


CRITIC_PROMPT = (
    "你是 ReflexLearn 的 Critic Agent。"
    "请分析失败资源任务的原因，输出可复用的反思经验。"
    "只输出 JSON，字段为 task_type、failure_type、cause、fix_strategy、success。"
)


async def critic_node(state: AgentState) -> dict:
    failed = [c for c in state.get("completed", []) if c.get("status") == "failed"]
    if not failed:
        return {"reflections": state.get("reflections", [])}

    llm = state.get("_llm")
    reflection = await _reflect_with_llm(llm, failed, state)
    if reflection is None:
        reflection = _fallback_reflection(failed)

    await _persist_reflection(reflection, state.get("user_id", "anonymous"))

    return {
        "reflections": state.get("reflections", []) + [reflection.model_dump()],
        "replan_count": state.get("replan_count", 0) + 1,
        "iteration": state.get("iteration", 0) + 1,
    }


async def _reflect_with_llm(llm, failed: list[dict], state: AgentState) -> Reflection | None:
    if llm is None:
        return None

    messages = [
        {"role": "system", "content": CRITIC_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "learning_goal": state.get("learning_goal", ""),
                    "failed_tasks": failed,
                    "learner_profile": state.get("learner_profile", {}),
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        completion = await llm.complete(
            messages,
            task_type="reasoning",
            schema=Reflection,
            temperature=0.1,
        )
        return Reflection.model_validate_json(completion.text)
    except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
        return None
    except Exception:
        return None


def _fallback_reflection(failed: list[dict]) -> Reflection:
    first = failed[0]
    issues = first.get("issues") or ["生成或校验失败"]
    return Reflection(
        task_type=first.get("type", "unknown"),
        failure_type="; ".join(str(issue) for issue in issues[:3]),
        cause="资源生成结果未通过质量门控",
        fix_strategy="降低任务难度，补充上下文，并在下一轮生成时显式修复失败点",
        success=False,
    )


async def _persist_reflection(reflection: Reflection, user_id: str) -> None:
    try:
        pg_pool = await get_pg_pool()
    except Exception:
        pg_pool = None

    try:
        qdrant = get_qdrant()
    except Exception:
        qdrant = None

    await write_reflection(
        pg_pool=pg_pool,
        qdrant=qdrant,
        reflection=reflection,
        user_id=user_id,
    )
