from __future__ import annotations

import asyncio

import pytest


def test_default_eval_cases_are_machine_learning_focused():
    from reflexlearn.eval.dataset import default_eval_cases

    cases = default_eval_cases()

    assert len(cases) >= 3
    assert all(case.case_id.startswith("ml-") for case in cases)
    assert {"doc", "quiz"}.issubset(set(cases[0].expected_resource_types))
    assert cases[0].difficulty_min <= cases[0].difficulty_max


@pytest.mark.asyncio
async def test_rule_judge_scores_resource_without_llm():
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.schemas import EvalCase, EvalResource

    case = EvalCase(
        case_id="ml-test",
        goal="学习线性回归",
        profile={"weak_points": ["数学推导"]},
        expected_resource_types=["doc"],
        reference_concepts=["线性回归", "梯度下降"],
        difficulty_min=0.2,
        difficulty_max=0.7,
        tags=["unit"],
    )
    resource = EvalResource(
        task_id="t1",
        type="doc",
        content="# 线性回归\n\n线性回归可以用梯度下降优化参数，适合监督学习入门。",
        difficulty=0.5,
    )

    score = await RuleJudge().evaluate(
        case=case,
        resource=resource,
        reference="线性回归 梯度下降 最小二乘法",
    )

    assert score.overall >= 0.7
    assert score.correctness > 0
    assert "rule" in score.reasoning


@pytest.mark.asyncio
async def test_llm_judge_uses_gateway_schema():
    import json

    from reflexlearn.eval.judge import LLMJudge
    from reflexlearn.eval.schemas import EvalCase, EvalResource, JudgeScore
    from reflexlearn.llm_gateway.gateway import Completion

    class FakeLLM:
        def __init__(self):
            self.calls: list[dict] = []

        async def complete(self, messages, **kwargs):
            self.calls.append({"messages": messages, "kwargs": kwargs})
            return Completion(
                text=json.dumps(
                    {
                        "correctness": 0.9,
                        "profile_match": 0.8,
                        "completeness": 0.7,
                        "format_quality": 0.6,
                        "overall": 0.75,
                        "reasoning": "llm judge ok",
                    },
                    ensure_ascii=False,
                )
            )

    llm = FakeLLM()
    judge = LLMJudge(llm)
    case = EvalCase(case_id="ml-test", goal="学习线性回归")
    resource = EvalResource(task_id="t1", type="doc", content="线性回归完整讲解")

    score = await judge.evaluate(case=case, resource=resource, reference="参考知识")

    assert score.overall == 0.75
    assert score.reasoning == "llm judge ok"
    assert llm.calls[0]["kwargs"]["task_type"] == "judgment"
    assert llm.calls[0]["kwargs"]["schema"] is JudgeScore
    assert llm.calls[0]["kwargs"]["temperature"] == 0.0


@pytest.mark.asyncio
async def test_llm_judge_falls_back_to_rules_when_gateway_fails():
    from reflexlearn.eval.judge import LLMJudge
    from reflexlearn.eval.schemas import EvalCase, EvalResource

    class FailingLLM:
        async def complete(self, messages, **kwargs):
            raise RuntimeError("llm unavailable")

    case = EvalCase(
        case_id="ml-test",
        goal="学习线性回归",
        expected_resource_types=["doc"],
        reference_concepts=["线性回归"],
        difficulty_min=0.1,
        difficulty_max=0.9,
    )
    resource = EvalResource(
        task_id="t1",
        type="doc",
        content="线性回归是一种监督学习方法，用于预测连续值。" * 3,
        difficulty=0.5,
    )

    score = await LLMJudge(FailingLLM()).evaluate(
        case=case,
        resource=resource,
        reference="线性回归",
    )

    assert score.correctness == 1.0
    assert score.reasoning.startswith("rule:")


@pytest.mark.asyncio
async def test_eval_runner_parses_langgraph_events_and_aggregates():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner

    async def fake_orchestrator(case):
        yield {"planner": {"plan": [{"type": "doc"}, {"type": "quiz"}]}}
        yield {
            "assemble": {
                "resource_bundle": {
                    "resources": [
                        {
                            "task_id": "doc-1",
                            "type": "doc",
                            "content": "线性回归 使用 最小二乘法 和 梯度下降 解决监督学习问题。" * 2,
                            "difficulty": 0.4,
                        },
                        {
                            "task_id": "quiz-1",
                            "type": "quiz",
                            "content": "题目：线性回归的损失函数是什么？答案：均方误差。" * 2,
                            "difficulty": 0.5,
                        },
                    ]
                }
            }
        }

    runner = EvalRunner(orchestrator=fake_orchestrator, judge=RuleJudge())
    report = await runner.run(default_eval_cases()[:1], strategy="unit")

    assert report.strategy == "unit"
    assert report.total_cases == 1
    assert report.task_completion_rate == 1.0
    assert report.avg_overall > 0
    assert report.results[0].resource_types_generated == ["doc", "quiz"]


@pytest.mark.asyncio
async def test_eval_runner_marks_timeout_as_failed():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner

    async def slow_orchestrator(case):
        await asyncio.sleep(0.05)
        yield {"assemble": {"resource_bundle": {"resources": []}}}

    runner = EvalRunner(
        orchestrator=slow_orchestrator,
        judge=RuleJudge(),
        per_case_timeout_s=0.01,
    )
    report = await runner.run(default_eval_cases()[:1], strategy="timeout")

    assert report.task_completion_rate == 0.0
    assert report.results[0].error == "timeout"


@pytest.mark.asyncio
async def test_eval_runner_records_trace_before_timeout():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner

    async def slow_after_planner(case):
        yield {"planner": {"plan": [{"type": "doc"}]}}
        await asyncio.sleep(0.05)
        yield {"assemble": {"resource_bundle": {"resources": []}}}

    runner = EvalRunner(
        orchestrator=slow_after_planner,
        judge=RuleJudge(),
        per_case_timeout_s=0.01,
    )
    report = await runner.run(default_eval_cases()[:1], strategy="timeout")
    result = report.results[0]

    assert result.error == "timeout"
    assert result.last_event == "planner"
    assert result.event_trace[0].node == "planner"
    assert result.event_trace[0].keys == ["plan"]
    assert "plan_types=doc" in result.event_trace[0].summary


def test_run_eval_script_contract():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    script = root / "scripts" / "jobs" / "run_eval.py"
    shell = root / "scripts" / "run_eval.sh"
    impl = root / "scripts" / "jobs" / "run_eval.sh"

    assert script.exists()
    assert 'exec "$SCRIPT_DIR/jobs/run_eval.sh" "$@"' in shell.read_text(encoding="utf-8")
    assert "$SCRIPTS_ROOT/jobs/run_eval.py" in impl.read_text(encoding="utf-8")
    assert "eval_report.md" in script.read_text(encoding="utf-8")
    assert "--compare" in script.read_text(encoding="utf-8")
    assert "eval_comparison.md" in script.read_text(encoding="utf-8")


def test_report_to_markdown_contains_summary_and_case_details():
    from reflexlearn.eval.report import report_to_markdown
    from reflexlearn.eval.schemas import EvalReport, EvalResult, JudgeScore

    report = EvalReport(
        strategy="unit",
        total_cases=1,
        task_completion_rate=1.0,
        avg_overall=0.88,
        results=[
            EvalResult(
                case_id="ml-001",
                strategy="unit",
                task_completed=True,
                resource_types_generated=["doc", "quiz"],
                resource_scores=[
                    JudgeScore(
                        correctness=0.9,
                        profile_match=0.8,
                        completeness=0.7,
                        format_quality=0.9,
                        overall=0.82,
                        reasoning="rule: ok",
                    )
                ],
                latency_ms=123,
            )
        ],
    )

    text = report_to_markdown(report)

    assert "# ReflexLearn 评测报告" in text
    assert "任务完成率" in text
    assert "ml-001" in text
    assert "doc, quiz" in text


def test_report_to_markdown_contains_last_event_for_timeout():
    from reflexlearn.eval.report import report_to_markdown
    from reflexlearn.eval.schemas import EvalReport, EvalResult, EvalTraceEvent

    report = EvalReport(
        strategy="timeout",
        total_cases=1,
        results=[
            EvalResult(
                case_id="ml-004",
                strategy="timeout",
                task_completed=False,
                error="timeout",
                last_event="planner",
                event_trace=[
                    EvalTraceEvent(
                        sequence=1,
                        node="planner",
                        elapsed_ms=12,
                        keys=["plan"],
                        summary="collab_mode=central; plan_types=doc",
                    )
                ],
            )
        ],
    )

    text = report_to_markdown(report)

    assert "最后事件" in text
    assert "最后摘要" in text
    assert "planner" in text
    assert "plan_types=doc" in text


def test_default_eval_strategies_include_ablation_profiles():
    from reflexlearn.eval.strategies import default_eval_strategies

    profiles = {item.name: item for item in default_eval_strategies()}

    assert {"full-smoke", "no_rag", "no_reflexion", "single_agent_baseline"}.issubset(profiles)
    assert profiles["full-smoke"].env["ENABLE_REFLEXION"] == "false"
    assert profiles["no_rag"].env["ENABLE_RAG"] == "false"
    assert profiles["no_rag"].env["ENABLE_REFLEXION"] == "false"
    assert profiles["no_reflexion"].env["ENABLE_REFLEXION"] == "false"
    assert profiles["no_reflexion"].env["ENABLE_LLM_PROFILE"] == "false"
    assert profiles["no_reflexion"].env["ENABLE_LLM_PLANNER"] == "false"
    assert profiles["no_reflexion"].env["EVAL_SKIP_PATH_PLAN"] == "true"
    assert profiles["no_reflexion"].env["OPENAI_COMPAT_API_KEY"] == ""
    assert profiles["single_agent_baseline"].env["EVAL_BASELINE"] == "single_agent"


def test_strategy_env_sets_and_restores_environment(monkeypatch):
    import os

    from reflexlearn.eval.strategies import EvalStrategy, strategy_env

    monkeypatch.setenv("ENABLE_RAG", "original")
    profile = EvalStrategy(
        name="unit",
        description="unit strategy",
        env={"ENABLE_RAG": "false", "ENABLE_MULTI_TURN": "false"},
    )

    with strategy_env(profile):
        assert os.environ["ENABLE_RAG"] == "false"
        assert os.environ["ENABLE_MULTI_TURN"] == "false"

    assert os.environ["ENABLE_RAG"] == "original"
    assert "ENABLE_MULTI_TURN" not in os.environ


@pytest.mark.asyncio
async def test_run_strategy_suite_runs_each_profile():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.runner import EvalRunner
    from reflexlearn.eval.schemas import EvalReport
    from reflexlearn.eval.strategies import EvalStrategy, run_strategy_suite

    class FakeRunner:
        async def run(self, cases, *, strategy):
            return EvalReport(
                strategy=strategy,
                total_cases=len(cases),
                task_completion_rate=1.0 if strategy == "full-smoke" else 0.5,
                avg_overall=0.8,
            )

    profiles = [
        EvalStrategy(name="full-smoke", description="full", env={}),
        EvalStrategy(name="no_rag", description="without rag", env={"ENABLE_RAG": "false"}),
    ]

    reports = await run_strategy_suite(
        default_eval_cases()[:1],
        profiles=profiles,
        runner_factory=lambda profile: FakeRunner(),
    )

    assert [report.strategy for report in reports] == ["full-smoke", "no_rag"]
    assert reports[1].task_completion_rate == 0.5


def test_comparison_to_markdown_contains_strategy_table():
    from reflexlearn.eval.report import comparison_to_markdown
    from reflexlearn.eval.schemas import EvalReport

    text = comparison_to_markdown(
        [
            EvalReport(strategy="full-smoke", total_cases=1, task_completion_rate=1.0, avg_overall=0.8),
            EvalReport(strategy="no_rag", total_cases=1, task_completion_rate=0.5, avg_overall=0.6),
        ]
    )

    assert "# ReflexLearn 消融对比报告" in text
    assert "| full-smoke |" in text
    assert "| no_rag |" in text
    assert "Δoverall" in text
    assert "任务完成率" in text


@pytest.mark.asyncio
async def test_single_agent_baseline_generates_only_doc_resource():
    from reflexlearn.eval.baselines import single_agent_baseline
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.runner import EvalRunner
    from reflexlearn.eval.judge import RuleJudge

    case = default_eval_cases()[0]
    events = [event async for event in single_agent_baseline(case)]
    resources = events[-1]["assemble"]["resource_bundle"]["resources"]

    assert [item["type"] for item in resources] == ["doc"]
    assert case.goal in resources[0]["content"]

    report = await EvalRunner(
        orchestrator=single_agent_baseline,
        judge=RuleJudge(),
    ).run([case], strategy="single_agent_baseline")

    assert report.results[0].resource_types_generated == ["doc"]
    assert report.avg_overall < 0.8
