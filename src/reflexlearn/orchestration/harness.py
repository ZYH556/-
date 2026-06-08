from __future__ import annotations

from reflexlearn.orchestration.state import AgentState
from reflexlearn.common.config import get_settings


def harness_guard(node_fn):
    async def guarded(state: AgentState) -> dict:
        settings = get_settings()
        iteration = state.get("iteration", 0)
        if iteration >= settings.max_iterations:
            return {"halt_reason": "max_iterations"}

        token_used = state.get("token_used", 0)
        if token_used >= settings.token_budget:
            return {"halt_reason": "token_budget"}

        result = await node_fn(state)
        return result

    guarded.__name__ = getattr(node_fn, "__name__", "guarded")
    return guarded
