from __future__ import annotations

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.state import AgentState


async def gate_node(state: AgentState) -> dict:
    return {"iteration": state.get("iteration", 0) + 1}


def gate_route(state: AgentState) -> str:
    if state.get("halt_reason"):
        return "assemble"

    if _has_conflict(state):
        return "debate"

    completed = state.get("completed", [])
    plan = state.get("plan", [])
    if not plan:
        return "assemble"

    failed = [c for c in completed if c.get("status") == "failed"]
    if failed and state.get("replan_count", 0) < get_settings().max_replan:
        return "critic"

    completed_ids = {c["task_id"] for c in completed if c.get("status") == "passed"}
    all_done = all(t["task_id"] in completed_ids for t in plan)
    if all_done:
        settings = get_settings()
        if (
            settings.enable_metacognition
            and state.get("self_refine_count", 0) < settings.max_self_refine
        ):
            return "metacognition"
        return "assemble"

    return "assemble"


def _has_conflict(state: AgentState) -> bool:
    conflict = state.get("conflict") or {}
    if conflict.get("has_conflict"):
        return True

    for task in state.get("plan", []):
        spec = task.get("spec", {})
        if spec.get("collab_mode") == "debate" or task.get("collab_mode") == "debate":
            return True

    return any(item.get("has_conflict") for item in state.get("completed", []))
