"""学习路径操作的数据模型与异常。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PathItemResource(BaseModel):
    resource_id: str
    title: str
    type: str = ""
    pinned: bool = False


class PathItemView(BaseModel):
    item_id: int
    sequence: int
    concept: str = ""
    objective: str = ""
    rationale: str = ""
    mastery_status: str = "not_started"
    resources: list[PathItemResource] = Field(default_factory=list)


class PathOpResult(BaseModel):
    ok: bool
    item_id: int = 0
    mastery_status: str = ""
    goal_progress: float = 0.0
    done_items: int = 0
    total_items: int = 0
    degraded: list[str] = Field(default_factory=list)


class PathOwnershipError(Exception):
    """节点或绑定资源不属于当前用户/租户。"""
