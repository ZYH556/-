from __future__ import annotations

from reflexlearn.memory.trim import trim_context, is_important, estimate_len, TrimConfig


def _u(c):
    return {"role": "user", "content": c}


def _a(c):
    return {"role": "assistant", "content": c}


def test_short_input_returned_asis():
    msgs = [_u("a"), _a("b")]
    out = trim_context(msgs, "", TrimConfig(recent_turns=6, max_chars=6000))
    assert out == [_u("a"), _a("b")]


def test_anchor_system_kept_on_top():
    msgs = [{"role": "system", "content": "规则"}, _u("a"), _a("b")]
    out = trim_context(msgs, "", TrimConfig(recent_turns=6))
    assert out[0] == {"role": "system", "content": "规则"}


def test_summary_context_injected_as_system():
    out = trim_context([_u("a"), _a("b")], "历史摘要内容", TrimConfig(recent_turns=6))
    assert any(m["role"] == "system" and "历史摘要内容" in m["content"] for m in out)


def test_recent_window_keeps_latest_drops_oldest():
    msgs = [_u(f"u{i}") for i in range(20)]
    out = trim_context(msgs, "", TrimConfig(recent_turns=2, max_chars=10000))
    contents = [m["content"] for m in out]
    assert "u19" in contents and "u18" in contents
    assert "u0" not in contents  # 最老的普通轮被丢


def test_important_middle_preserved():
    msgs = [_u("普通闲聊"), _u("这里有重要决策点"), _u("r1"), _u("r2")]
    out = trim_context(msgs, "", TrimConfig(recent_turns=1, max_chars=10000))
    contents = [m["content"] for m in out]
    assert "这里有重要决策点" in contents  # 重要中段保留
    assert "普通闲聊" not in contents  # 普通中段丢弃


def test_char_budget_limits_middle():
    big = "x" * 5000
    msgs = [_u(big + "失败一"), _u(big + "失败二"), _u(big + "失败三"), _u("r1"), _u("r2")]
    out = trim_context(msgs, "", TrimConfig(recent_turns=1, max_chars=6000))
    important_kept = [m for m in out if "失败" in m["content"]]
    assert len(important_kept) == 1  # 预算只够 1 条中段重要轮


def test_is_important():
    assert is_important(_u("这次任务失败了")) is True
    assert is_important(_u("你好呀")) is False
    assert is_important({"role": "tool", "content": "x"}) is True


def test_normalizes_langchain_like_objects():
    class _Msg:
        def __init__(self, t, c):
            self.type = t
            self.content = c

    out = trim_context([_Msg("human", "hi"), _Msg("ai", "yo")], "", TrimConfig(recent_turns=6))
    assert out == [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]


def test_estimate_len():
    assert estimate_len([_u("abc"), _a("de")]) == 5
