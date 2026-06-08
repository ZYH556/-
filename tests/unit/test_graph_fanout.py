from __future__ import annotations

from langgraph.types import Send

from reflexlearn.orchestration.graph import fan_out


def task(task_id: str, status: str = "pending") -> dict:
    return {
        "task_id": task_id,
        "type": "doc",
        "spec": {"type": "doc", "concept_ids": [task_id]},
        "status": status,
        "attempts": 0,
        "result_ref": None,
    }


def test_fan_out_sends_each_pending_task():
    state = {"plan": [task("t1"), task("t2"), task("t3", "passed")]}

    sends = fan_out(state)

    assert len(sends) == 2
    assert all(isinstance(item, Send) for item in sends)
    assert [item.arg["_current_task"]["task_id"] for item in sends] == ["t1", "t2"]


def test_fan_out_returns_empty_when_no_pending_task():
    state = {"plan": [task("t1", "passed")]}

    assert fan_out(state) == []
