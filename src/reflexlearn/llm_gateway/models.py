"""LLMGateway 的数据模型（拆出以避免 gateway↔streaming 循环导入 + 守行预算）。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Completion(BaseModel):
    text: str
    model_used: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class StreamChunk(BaseModel):
    """流式增量帧：delta 为本次新增文本；done=True 为末帧，带聚合 Completion。
    degraded=True 表示走了一次性回退（中转站不支持流式 / 流式中途失败）。"""

    delta: str = ""
    done: bool = False
    completion: Optional[Completion] = None
    degraded: bool = False
