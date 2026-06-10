from __future__ import annotations

from reflexlearn.orchestration.nodes.reflection.metacognition import metacognition_route


def test_metacognition_route_refines_only_tasks_with_hint():
    state = {
        "plan": [
            {"task_id": "t1", "status": "pending", "spec": {"refine_hint": "补例子"}},
            {"task_id": "t2", "status": "pending", "spec": {}},
        ]
    }

    sends = metacognition_route(state)

    assert len(sends) == 1
    assert sends[0].node == "generate_resource"
    assert sends[0].arg["_current_task"]["task_id"] == "t1"
