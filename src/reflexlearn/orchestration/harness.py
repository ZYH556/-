from __future__ import annotations

import time

from reflexlearn.orchestration.state import AgentState
from reflexlearn.common.config import get_settings
from reflexlearn.observability.metrics import observe_agent_node


def harness_guard(node_fn):
    async def guarded(state: AgentState) -> dict:
        node_name = getattr(node_fn, "__name__", "guarded")
        start = time.perf_counter()
        status = "ok"
        settings = get_settings()
        try:
            iteration = state.get("iteration", 0)
            if iteration >= settings.max_iterations:
                status = "halted"
                return {"halt_reason": "max_iterations"}

            token_used = state.get("token_used", 0)
            if token_used >= settings.token_budget:
                status = "halted"
                return {"halt_reason": "token_budget"}

            result = await node_fn(state)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            observe_agent_node(node_name, status, time.perf_counter() - start)

    guarded.__name__ = getattr(node_fn, "__name__", "guarded")
    return guarded
