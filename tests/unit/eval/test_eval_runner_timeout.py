from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_eval_runner_falls_back_when_judge_exceeds_case_budget():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.runner import EvalRunner

    class SlowJudge:
        async def evaluate(self, **kwargs):
            await asyncio.sleep(0.05)
            raise AssertionError("slow judge should be cancelled")

    async def fast_orchestrator(case):
        yield {
            "assemble": {
                "resource_bundle": {
                    "resources": [
                        {
                            "task_id": "doc-1",
                            "type": "doc",
                            "content": "线性回归是一种监督学习方法。" * 8,
                            "difficulty": 0.4,
                        }
                    ]
                }
            }
        }

    runner = EvalRunner(
        orchestrator=fast_orchestrator,
        judge=SlowJudge(),
        per_case_timeout_s=0.01,
    )
    report = await runner.run(default_eval_cases()[:1], strategy="judge-timeout")
    result = report.results[0]

    assert result.task_completed is True
    assert result.error == "judge_timeout_rule_fallback"
    assert result.resource_scores[0].reasoning.startswith("rule:")
