from __future__ import annotations

from reflexlearn.orchestration.state import AgentState


async def assemble_node(state: AgentState) -> dict:
    completed = state.get("completed", [])
    resources = [c for c in completed if c.get("status") == "passed"]

    bundle = {
        "goal": state.get("learning_goal", ""),
        "resources": resources,
        "total": len(resources),
        "profile_summary": {
            "cognitive_style": state.get("learner_profile", {}).get("cognitive_style", ""),
            "weak_points": state.get("learner_profile", {}).get("weak_points", []),
        },
    }

    path = [
        {"sequence": i + 1, "resource_type": r.get("type", "doc"), "task_id": r["task_id"]}
        for i, r in enumerate(resources)
    ]

    return {"resource_bundle": bundle, "learning_path": path}
