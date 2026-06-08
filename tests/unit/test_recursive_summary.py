from __future__ import annotations

import pytest

from reflexlearn.memory.recursive_summary import (
    add_and_compress,
    get_context,
    SummaryConfig,
)


class _SummaryLLM:
    """summary 任务返回固定短摘要；fail=True 模拟 llm_no_api_key 触发降级。"""

    def __init__(self, fail: bool = False, text: str = "摘要S"):
        self.fail = fail
        self.text = text
        self.calls: list[str] = []

    async def complete(self, messages, *, task_type="generation", schema=None, temperature=0.7):
        from reflexlearn.llm_gateway.gateway import Completion

        self.calls.append(task_type)
        if self.fail:
            raise RuntimeError("llm_no_api_key")
        return Completion(text=self.text)


def test_get_context_empty():
    assert get_context([]) == ""
    assert get_context(None) == ""


def test_get_context_joins():
    assert get_context(["a", "b"]) == "a\n---\nb"


@pytest.mark.asyncio
async def test_add_with_llm_appends_layer():
    llm = _SummaryLLM()
    layers = await add_and_compress([], [{"role": "user", "content": "线性回归讨论"}], llm)
    assert layers == ["摘要S"]
    assert "summary" in llm.calls  # 走了成本感知的 summary task_type


@pytest.mark.asyncio
async def test_add_no_llm_rule_truncate():
    layers = await add_and_compress([], [{"role": "user", "content": "内容X"}], None)
    assert len(layers) == 1
    assert "离线摘要" in layers[0]
    assert "内容X" in layers[0]


@pytest.mark.asyncio
async def test_add_llm_fail_degrades_to_rule():
    llm = _SummaryLLM(fail=True)
    layers = await add_and_compress([], [{"role": "user", "content": "内容Y"}], llm)
    assert len(layers) == 1
    assert "离线摘要" in layers[0]


@pytest.mark.asyncio
async def test_empty_new_messages_returns_layers_unchanged():
    layers = await add_and_compress(["L1"], [], None)
    assert layers == ["L1"]


@pytest.mark.asyncio
async def test_max_depth_merges_oldest_with_llm():
    cfg = SummaryConfig(max_depth=3)
    llm = _SummaryLLM()
    # 已有 3 层 + 新增 1 层 = 4 > max_depth → 合并最老两层 → 3 层
    layers = await add_and_compress(["A", "B", "C"], [{"role": "user", "content": "new"}], llm, cfg)
    assert len(layers) == 3


@pytest.mark.asyncio
async def test_merge_no_llm_concatenates():
    cfg = SummaryConfig(max_depth=2)
    # 已有 2 层 + 规则截断新增 1 层 = 3 > 2 → 无 llm 合并最老两层为字符串拼接
    layers = await add_and_compress(["A", "B"], [{"role": "user", "content": "C内容"}], None, cfg)
    assert len(layers) == 2
    assert "A / B" in layers[0]
