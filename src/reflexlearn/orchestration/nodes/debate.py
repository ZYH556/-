from __future__ import annotations

import asyncio
import json

from pydantic import ValidationError

from reflexlearn.orchestration.schemas import DebateResult
from reflexlearn.orchestration.state import AgentState


MAX_DEBATE_ROUNDS = 3
DEBATER_PROMPT = (
    "你是辩论型学习资源审查员。"
    "请基于给定证据片段形成一个简洁立场摘要，只输出 JSON。"
    "字段为 perspective、claim、evidence_summary、confidence。"
)
JUDGE_PROMPT = (
    "你是辩论裁决器。"
    "请根据多轮立场摘要裁决最可信结论，只输出 JSON。"
    "字段为 winner_position、reasoning、confidence。"
)


async def debate_node(state: AgentState) -> dict:
    conflict = _resolve_conflict(state)
    chunks = conflict.get("chunks", [])
    if not chunks:
        return {"debate_rounds": [], "iteration": state.get("iteration", 0) + 1}

    llm = state.get("_llm")
    rounds: list[dict] = []
    for round_index in range(MAX_DEBATE_ROUNDS):
        positions = await asyncio.gather(
            *[_debater_round(chunk, rounds, state, llm) for chunk in chunks]
        )
        rounds.append({"round": round_index + 1, "positions": positions})
        if _has_converged(rounds):
            break

    return {"debate_rounds": rounds, "iteration": state.get("iteration", 0) + 1}


async def judge_node(state: AgentState) -> dict:
    llm = state.get("_llm")
    rounds = state.get("debate_rounds") or []
    result = await _judge_with_llm(llm, rounds)
    if result is None:
        result = _fallback_verdict(rounds)

    # 辩论结论作为一个 passed 资源写入 completed（带 add reducer），
    # 交由下游 assemble_node 统一纳入 resource_bundle / learning_path。
    # 不在此处自行构造 bundle —— 那样会被随后的 assemble_node 覆盖（无 reducer，last-write-wins）。
    return {
        "debate_verdict": result.model_dump(),
        "completed": [
            {
                "task_id": "debate-verdict",
                "status": "passed",
                "type": "debate",
                "content": result.reasoning,
                "winner_position": result.winner_position,
                "confidence": result.confidence,
            }
        ],
        "iteration": state.get("iteration", 0) + 1,
    }


async def _debater_round(chunk: dict, rounds: list[dict], state: AgentState, llm) -> dict:
    if llm is None:
        return _fallback_position(chunk)

    messages = [
        {"role": "system", "content": DEBATER_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "learning_goal": state.get("learning_goal", ""),
                    "evidence_chunk": chunk,
                    "previous_round_summaries": _summarize_rounds(rounds),
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        completion = await llm.complete(messages, task_type="reasoning", temperature=0.2)
        parsed = json.loads(completion.text)
        return {
            "perspective": str(parsed.get("perspective", chunk.get("source", "unknown"))),
            "claim": str(parsed.get("claim", "")),
            "evidence_summary": str(parsed.get("evidence_summary", "")),
            "confidence": _clamp_unit(parsed.get("confidence"), 0.5),
        }
    except Exception:
        return _fallback_position(chunk)


async def _judge_with_llm(llm, rounds: list[dict]) -> DebateResult | None:
    if llm is None:
        return None

    messages = [
        {"role": "system", "content": JUDGE_PROMPT},
        {"role": "user", "content": json.dumps(rounds, ensure_ascii=False)},
    ]
    try:
        completion = await llm.complete(
            messages,
            task_type="reasoning",
            schema=DebateResult,
            temperature=0.0,
        )
        return DebateResult.model_validate_json(completion.text)
    except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
        return None
    except Exception:
        return None


def _resolve_conflict(state: AgentState) -> dict:
    if state.get("conflict"):
        return state["conflict"] or {}

    for task in state.get("plan", []):
        spec = task.get("spec", {})
        if spec.get("collab_mode") == "debate" or task.get("collab_mode") == "debate":
            chunks = spec.get("conflict_chunks") or [
                {"source": "planner-a", "content": "正方观点：该结论成立。"},
                {"source": "planner-b", "content": "反方观点：该结论需要限定条件。"},
            ]
            return {"has_conflict": True, "chunks": chunks}

    completed = state.get("completed", [])
    conflicts = [c for c in completed if c.get("has_conflict")]
    if conflicts:
        return {"has_conflict": True, "chunks": conflicts}
    return {}


def _clamp_unit(value, default: float = 0.5) -> float:
    """把任意输入归一到 [0, 1]，非法/越界值回退到 default，避免 confidence 触发 DebateResult 的 ge/le 校验。"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(num, 0.0), 1.0)


def _fallback_position(chunk: dict) -> dict:
    return {
        "perspective": chunk.get("source", "unknown"),
        "claim": chunk.get("content", "")[:120],
        "evidence_summary": chunk.get("content", "")[:200],
        "confidence": _clamp_unit(chunk.get("relevance_score"), 0.5),
    }


def _fallback_verdict(rounds: list[dict]) -> DebateResult:
    positions = rounds[-1]["positions"] if rounds else []
    winner = max(positions, key=lambda item: item.get("confidence", 0.0), default={})
    return DebateResult(
        winner_position=winner.get("claim") or winner.get("perspective", "无明确胜出立场"),
        reasoning=winner.get("evidence_summary", "缺少可裁决证据，保留争议并进入人工复核。"),
        confidence=_clamp_unit(winner.get("confidence"), 0.3),
    )


def _summarize_rounds(rounds: list[dict]) -> list[dict]:
    summaries = []
    for item in rounds[-2:]:
        summaries.append(
            {
                "round": item.get("round"),
                "positions": [
                    {
                        "perspective": pos.get("perspective", ""),
                        "claim": pos.get("claim", ""),
                    }
                    for pos in item.get("positions", [])
                ],
            }
        )
    return summaries


def _has_converged(rounds: list[dict]) -> bool:
    if len(rounds) < 2:
        return False
    previous = {p.get("claim", "") for p in rounds[-2].get("positions", [])}
    current = {p.get("claim", "") for p in rounds[-1].get("positions", [])}
    return previous == current
