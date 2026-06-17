"""PERF · rag.model_infer.run_model：模型推理丢线程（不阻塞事件循环）+ 全局串行。"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from reflexlearn.rag.model_infer import run_model


@pytest.mark.asyncio
async def test_run_model_does_not_block_event_loop():
    """同步阻塞 0.3s 的「模型」经 run_model 丢线程时，事件循环仍能并发推进其它协程。"""
    order: list[str] = []

    async def model():
        await run_model(time.sleep, 0.3)
        order.append("model")

    async def probe():
        await asyncio.sleep(0.05)
        order.append("probe")

    await asyncio.gather(model(), probe())
    # probe 在 model 的同步 sleep 期间就完成 → 事件循环未被阻塞（修复前会是 model 先）
    assert order == ["probe", "model"]


@pytest.mark.asyncio
async def test_run_model_serializes_inference():
    """全局锁保证任意时刻只有一个推理在跑（守 OOM/双模型不并发铁律）。"""
    active = 0
    max_active = 0
    guard = threading.Lock()

    def work():
        nonlocal active, max_active
        with guard:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with guard:
            active -= 1

    await asyncio.gather(*[run_model(work) for _ in range(4)])
    assert max_active == 1


@pytest.mark.asyncio
async def test_run_model_returns_value_and_propagates_exc():
    assert await run_model(lambda x: x * 2, 21) == 42

    with pytest.raises(ValueError, match="boom"):
        await run_model(_raise)


def _raise():
    raise ValueError("boom")
