from __future__ import annotations

import pytest

from reflexlearn.common.config import get_settings
from reflexlearn.orchestration.nodes.core.generator import generate_resource
from reflexlearn.skills.base import SkillResult


class FakeRetrieveSkill:
    async def run(self, inp, ctx):
        return SkillResult(ok=True, data={"chunks": [{"content": "线性回归上下文"}]})


class FakeGenSkill:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        index = min(len(self.calls) - 1, len(self.contents) - 1)
        return SkillResult(ok=True, data={"content": self.contents[index]})


class FakeQualitySkill:
    def __init__(self, checks: list[dict]):
        self.checks = checks
        self.calls: list[dict] = []

    async def run(self, inp, ctx):
        self.calls.append(inp)
        index = min(len(self.calls) - 1, len(self.checks) - 1)
        return SkillResult(ok=True, data=self.checks[index])


def base_state(gen_skill, quality_skill) -> dict:
    return {
        "user_id": "u1",
        "acl": {},
        "messages": [],
        "learner_profile": {"cognitive_style": "active"},
        "learning_goal": "学习线性回归",
        "plan": [
            {
                "task_id": "task-1",
                "type": "doc",
                "spec": {
                    "type": "doc",
                    "concept_ids": ["linear_regression"],
                    "difficulty": 0.5,
                    "style_hint": "active",
                    "constraints": [],
                },
                "status": "pending",
                "attempts": 0,
                "result_ref": None,
            }
        ],
        "completed": [],
        "reflections": [],
        "iteration": 0,
        "replan_count": 0,
        "token_used": 0,
        "halt_reason": None,
        "conflict": None,
        "debate_rounds": None,
        "debate_verdict": None,
        "resource_bundle": None,
        "learning_path": None,
        "_skills": {
            "retrieve": FakeRetrieveSkill(),
            "doc_gen": gen_skill,
            "quality_check": quality_skill,
        },
    }


@pytest.mark.asyncio
async def test_generator_retries_after_fixable_quality_failure():
    gen = FakeGenSkill(["短内容", "这是第二次生成的完整学习文档，包含概念解释、例子和总结。"])
    quality = FakeQualitySkill(
        [
            {"passed": False, "issues": ["内容过短"], "fixable": True},
            {"passed": True, "issues": [], "fixable": True},
        ]
    )

    result = await generate_resource(base_state(gen, quality))

    completed = result["completed"][0]
    assert completed["status"] == "passed"
    assert completed["react_steps"] == 2
    assert len(gen.calls) == 2
    assert gen.calls[1]["spec"]["previous_issues"] == ["内容过短"]


@pytest.mark.asyncio
async def test_generator_stops_on_unfixable_quality_failure():
    gen = FakeGenSkill(["错误内容"])
    quality = FakeQualitySkill(
        [{"passed": False, "issues": ["知识错误"], "fixable": False}]
    )

    result = await generate_resource(base_state(gen, quality))

    completed = result["completed"][0]
    assert completed["status"] == "failed"
    assert completed["issues"] == ["知识错误"]
    assert len(gen.calls) == 1


@pytest.mark.asyncio
async def test_generator_diagnostics_records_internal_stages(monkeypatch, caplog):
    monkeypatch.setenv("ENABLE_GENERATOR_DIAGNOSTICS", "true")
    get_settings.cache_clear()
    gen = FakeGenSkill(["这是完整学习文档，包含概念解释、例子和总结。"])
    quality = FakeQualitySkill([{"passed": True, "issues": [], "fixable": True}])

    try:
        with caplog.at_level("INFO", logger="reflexlearn.orchestration.nodes.core.generator"):
            result = await generate_resource(base_state(gen, quality))
    finally:
        get_settings.cache_clear()

    assert result["completed"][0]["status"] == "passed"
    messages = "\n".join(record.message for record in caplog.records)
    assert "generator_diag stage=retrieve_start" in messages
    assert "generator_diag stage=generation_end" in messages
    assert "generator_diag stage=quality_end" in messages
    assert "generator_diag stage=task_end" in messages


class StreamingGenSkill:
    """读 ctx.delta_sink 并逐段推增量的假生成 Skill（模拟 doc_gen 流式）。"""

    def __init__(self, pieces: list[str]):
        self.pieces = pieces

    async def run(self, inp, ctx):
        sink = getattr(ctx, "delta_sink", None)
        for p in self.pieces:
            if sink:
                sink(p)
        return SkillResult(ok=True, data={"content": "".join(self.pieces)})


@pytest.mark.asyncio
async def test_generator_emits_deltas_through_stream_writer(monkeypatch):
    import reflexlearn.orchestration.nodes.core.generator as gen_mod

    frames: list[dict] = []
    monkeypatch.setattr(gen_mod, "_stream_writer", lambda: frames.append)

    gen = StreamingGenSkill(["线性", "回归"])
    quality = FakeQualitySkill([{"passed": True, "issues": [], "fixable": True}])

    result = await generate_resource(base_state(gen, quality))

    assert result["completed"][0]["status"] == "passed"
    # 首帧 reset 清场，随后逐 token 增量；每帧带 task_id 供前端按 fan-out 分路
    assert frames[0]["reset"] is True
    deltas = [f["delta"] for f in frames if f["delta"]]
    assert deltas == ["线性", "回归"]
    assert all(f["task_id"] == "task-1" for f in frames)


@pytest.mark.asyncio
async def test_generator_no_writer_skips_streaming(monkeypatch):
    """无流式 run 上下文（_stream_writer→None）时不构造 sink，照常一次性生成。"""
    import reflexlearn.orchestration.nodes.core.generator as gen_mod

    monkeypatch.setattr(gen_mod, "_stream_writer", lambda: None)

    gen = StreamingGenSkill(["这是完整文档内容，包含解释与总结，长度足够通过质检。"])
    quality = FakeQualitySkill([{"passed": True, "issues": [], "fixable": True}])

    result = await generate_resource(base_state(gen, quality))

    assert result["completed"][0]["status"] == "passed"
