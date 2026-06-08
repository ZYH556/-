from __future__ import annotations

from typing import Annotated, Literal, Optional, TypedDict
from operator import add

from langgraph.graph.message import add_messages

ResourceType = Literal["doc", "mindmap", "quiz", "reading", "code", "video"]


class ResourceTask(TypedDict):
    task_id: str
    type: ResourceType
    spec: dict
    status: Literal["pending", "running", "passed", "failed"]
    attempts: int
    result_ref: Optional[str]


class AgentState(TypedDict):
    user_id: str
    session_id: str
    acl: dict
    messages: Annotated[list, add_messages]
    summary_layers: list[str]

    learner_profile: dict
    learning_goal: str
    collab_mode: Optional[str]

    plan: list[ResourceTask]
    completed: Annotated[list[dict], add]

    reflections: list[dict]

    iteration: int
    replan_count: int
    token_used: int
    halt_reason: Optional[str]

    conflict: Optional[dict]
    debate_rounds: Optional[list[dict]]
    debate_verdict: Optional[dict]

    resource_bundle: Optional[dict]
    learning_path: Optional[list[dict]]
    path_summary: Optional[str]
    path_strategy: Optional[str]
