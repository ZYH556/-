from __future__ import annotations

import pytest


class _CountingJudge:
    def __init__(self):
        self.calls: list[str] = []

    async def evaluate(self, *, case, resource, reference: str = ""):
        from reflexlearn.eval.schemas import JudgeScore

        self.calls.append(resource.task_id)
        return JudgeScore(
            correctness=0.8,
            profile_match=0.8,
            completeness=0.8,
            format_quality=0.8,
            overall=0.8,
            reasoning="llm judge ok",
        )


@pytest.mark.asyncio
async def test_eval_runner_limits_judged_resources_by_setting(monkeypatch):
    monkeypatch.setenv("EVAL_JUDGE_MAX_RESOURCES", "1")
    from reflexlearn.common.config import get_settings
    from reflexlearn.eval.runner import EvalRunner
    from reflexlearn.eval.schemas import EvalCase

    get_settings.cache_clear()
    case = EvalCase(
        case_id="perf-001",
        goal="元认知性能治理",
        expected_resource_types=["doc", "quiz", "code"],
    )

    async def fake_orchestrator(_case):
        yield {
            "assemble": {
                "resource_bundle": {
                    "resources": [
                        {"task_id": "quiz-1", "type": "quiz", "content": "quiz" * 90},
                        {"task_id": "code-1", "type": "code", "content": "code" * 90},
                        {"task_id": "doc-1", "type": "doc", "content": "doc" * 90},
                    ]
                }
            }
        }

    judge = _CountingJudge()
    try:
        report = await EvalRunner(orchestrator=fake_orchestrator, judge=judge).run(
            [case],
            strategy="metacognition_real_on",
        )
    finally:
        get_settings.cache_clear()

    result = report.results[0]
    assert judge.calls == ["doc-1"]
    assert result.resource_types_generated == ["quiz", "code", "doc"]
    assert result.resource_coverage == 1.0
    assert len(result.resource_scores) == 1
    assert result.resource_scores[0].reasoning == "llm judge ok"


def test_real_metacognition_strategy_limits_judge_to_one_resource():
    from reflexlearn.eval.strategies import default_eval_strategies

    profiles = {item.name: item for item in default_eval_strategies()}

    assert profiles["metacognition_real_on"].env["EVAL_JUDGE_MAX_RESOURCES"] == "1"
    assert profiles["metacognition_real_off"].env["EVAL_JUDGE_MAX_RESOURCES"] == "1"
    assert profiles["metacognition_real_on"].env["METACOGNITION_TIMEOUT_S"] == "20"


def test_metacognition_prompt_demands_refine_for_offline_placeholder():
    from reflexlearn.orchestration.nodes.reflection.metacognition import _PROMPT

    assert "离线占位" in _PROMPT
    assert "refine_hint" in _PROMPT


def test_offline_doc_includes_refine_issues():
    from reflexlearn.skills.offline import offline_content

    content = offline_content(
        "doc",
        {
            "concept_ids": ["线性回归质量校验失败"],
            "previous_issues": ["补充失败归因流程和修复策略"],
        },
    )

    assert "元认知修复建议" in content
    assert "补充失败归因流程和修复策略" in content
