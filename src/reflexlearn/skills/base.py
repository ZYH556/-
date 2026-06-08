from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class SkillContext(BaseModel):
    user_id: str
    acl: dict
    task_id: str
    trace_id: str = ""


class SkillResult(BaseModel):
    ok: bool
    data: Optional[dict] = None
    error_type: Optional[str] = None
    duration_ms: int = 0
    cached: bool = False


@runtime_checkable
class Skill(Protocol):
    name: str
    max_calls_per_task: int
    cache_ttl: Optional[int]

    async def run(self, inp: dict, ctx: SkillContext) -> SkillResult: ...
