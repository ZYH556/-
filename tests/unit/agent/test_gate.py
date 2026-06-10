from __future__ import annotations

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.nodes.core.gate import gate_route


def base_state() -> dict:
    return {
        "halt_reason": None,
        "replan_count": 0,
        "plan": [{"task_id": "t1"}],
        "completed": [],
        "conflict": None,
    }


def test_gate_routes_failed_task_to_critic():
    state = base_state()
    state["completed"] = [{"task_id": "t1", "status": "failed"}]

    assert gate_route(state) == "critic"


def test_gate_routes_to_assemble_when_all_passed():
    state = base_state()
    state["completed"] = [{"task_id": "t1", "status": "passed"}]

    assert gate_route(state) == "assemble"


def test_gate_routes_to_assemble_when_replan_limit_reached():
    state = base_state()
    state["completed"] = [{"task_id": "t1", "status": "failed"}]
    state["replan_count"] = get_settings().max_replan

    assert gate_route(state) == "assemble"


def test_gate_routes_conflict_to_debate():
    state = base_state()
    state["conflict"] = {"has_conflict": True, "chunks": []}

    assert gate_route(state) == "debate"
