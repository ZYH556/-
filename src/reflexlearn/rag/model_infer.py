"""RAG 模型推理的事件循环友好封装（PERF · fan-out 并行化）。

并发 fan-out 下 N 个资源各自 retrieve 会同时触发 embedding/rerank。直接同步调用
`model.encode()/predict()` 会**阻塞事件循环**——其它资源的 LLM I/O 无法在此期间推进，
扇出退化为串行（docs/19 §6 实测：retrieve 在链路上时扇出 18.59s，移除后 4.34s）。

本封装把同步推理丢进线程（`asyncio.to_thread`）→ 事件循环让出 → 各资源的 LLM 调用得以
重叠；同时用**全局 threading.Lock 串行化实际推理**——绝不让 embedding 与 reranker 推理
并发，守 OOM/死锁铁律（见 memory「双模型错峰防死锁」「双份 bge 模型死锁」）。

threading.Lock（非 asyncio）刻意为之：loop 无关、不存在「绑定到不同事件循环」的坑
（单测每用例新建 loop），且天然跨线程串行。
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable, TypeVar

T = TypeVar("T")

# 全局推理锁：embedding 与 reranker 共用一把，保证任意时刻只有一个模型在推理。
_model_lock = threading.Lock()


def _serial(fn: Callable[..., T], args: tuple, kwargs: dict) -> T:
    with _model_lock:
        return fn(*args, **kwargs)


async def run_model(fn: Callable[..., T], *args, **kwargs) -> T:
    """在线程中串行执行同步模型推理；事件循环在此期间空闲，可调度其它协程。"""
    return await asyncio.to_thread(_serial, fn, args, kwargs)
