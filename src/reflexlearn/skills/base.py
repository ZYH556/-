from __future__ import annotations

from typing import Callable, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class SkillContext(BaseModel):
    # delta_sink 是运行期回调（非数据），需允许任意类型
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    acl: dict
    task_id: str
    trace_id: str = ""
    # 流式增量回调（PERF-A）：散文型生成 Skill 每产出一段文本即调用；None=不流式。
    delta_sink: Optional[Callable[[str], None]] = None


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
