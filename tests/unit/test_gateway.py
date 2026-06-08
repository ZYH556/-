from __future__ import annotations

import pytest

from reflexlearn.llm_gateway.gateway import LLMGateway


class _S:
    """最小 settings 替身，只含 _select_model / _get_api_key 关心的字段。"""

    def __init__(self, **kw):
        self.deepseek_api_key = kw.get("deepseek", "")
        self.qwen_api_key = kw.get("qwen", "")
        self.anthropic_api_key = kw.get("anthropic", "")
        self.summary_model = kw.get("summary_model", "")


def _gw(**kw) -> LLMGateway:
    gw = LLMGateway()
    gw._settings = _S(**kw)
    return gw


# —— summary 成本感知路由：走便宜档 ——

def test_summary_uses_cheaper_qwen():
    gw = _gw(qwen="k")
    assert gw._select_model("summary") == "openai/qwen-turbo"
    # 非便宜任务仍走 qwen-plus（改造前行为）
    assert gw._select_model("planning") == "openai/qwen-plus"


def test_summary_uses_cheaper_anthropic():
    gw = _gw(anthropic="k")
    assert gw._select_model("summary") == "anthropic/claude-haiku-4-5"
    assert gw._select_model("generation") == "anthropic/claude-sonnet-4-6"


def test_summary_model_override_takes_precedence():
    gw = _gw(qwen="k", summary_model="openai/custom-cheap")
    assert gw._select_model("summary") == "openai/custom-cheap"
    # 覆盖只作用于便宜任务，不影响其它
    assert gw._select_model("planning") == "openai/qwen-plus"


def test_deepseek_has_no_cheaper_tier():
    gw = _gw(deepseek="k")
    assert gw._select_model("summary") == "deepseek/deepseek-chat"
    assert gw._select_model("planning") == "deepseek/deepseek-chat"


# —— 零回归：非 summary 任务选型与改造前逐字节一致 ——

def test_non_summary_selection_unchanged():
    assert _gw(deepseek="k")._select_model("planning") == "deepseek/deepseek-chat"
    assert _gw(qwen="k")._select_model("profiling") == "openai/qwen-plus"
    assert _gw(anthropic="k")._select_model("generation") == "anthropic/claude-sonnet-4-6"
    assert _gw()._select_model("planning") == "deepseek/deepseek-chat"  # 全空默认


def test_provider_priority_deepseek_first():
    # deepseek 优先于 qwen 优先于 anthropic（改造前优先级不变）
    gw = _gw(deepseek="d", qwen="q", anthropic="a")
    assert gw._select_model("summary") == "deepseek/deepseek-chat"
    assert gw._select_model("planning") == "deepseek/deepseek-chat"


# —— 无凭证：仍抛 llm_no_api_key（降级铁律入口） ——

@pytest.mark.asyncio
async def test_no_api_key_raises_for_summary():
    gw = _gw()  # 全空
    with pytest.raises(RuntimeError, match="llm_no_api_key"):
        await gw.complete([{"role": "user", "content": "hi"}], task_type="summary")


def test_get_api_key_matches_cheaper_models():
    # 新增便宜档模型名仍能正确映射回各自 provider 的 key
    gw = _gw(qwen="qk", anthropic="ak")
    assert gw._get_api_key("openai/qwen-turbo") == "qk"
    assert gw._get_api_key("anthropic/claude-haiku-4-5") == "ak"
