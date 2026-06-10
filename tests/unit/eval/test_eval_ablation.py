from __future__ import annotations

import pytest


def test_default_eval_cases_include_ablation_slices():
    from reflexlearn.eval.dataset import default_eval_cases

    cases = default_eval_cases()
    by_id = {case.case_id: case for case in cases}

    assert "ml-004" in by_id
    assert "ml-005" in by_id
    assert {"ablation", "rag_required"}.issubset(set(by_id["ml-004"].tags))
    assert {"ablation", "reflexion_required"}.issubset(set(by_id["ml-005"].tags))
    assert "Qdrant" in by_id["ml-004"].reference_concepts
    assert "失败归因" in by_id["ml-005"].reference_concepts


def test_select_eval_cases_filters_by_all_tags_and_limit():
    from reflexlearn.eval.dataset import select_eval_cases

    rag_cases = select_eval_cases(tags=["ablation", "rag_required"])
    ablation_cases = select_eval_cases(tags=["ablation"], max_cases=1)

    assert [case.case_id for case in rag_cases] == ["ml-004"]
    assert len(ablation_cases) == 1
    assert "ablation" in ablation_cases[0].tags


@pytest.mark.asyncio
async def test_eval_runner_reports_expected_resource_coverage():
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner
    from reflexlearn.eval.schemas import EvalCase

    case = EvalCase(
        case_id="coverage-001",
        goal="学习资源覆盖率",
        expected_resource_types=["doc", "quiz", "code"],
        reference_concepts=["线性回归"],
    )

    async def fake_orchestrator(_case):
        yield {
            "assemble": {
                "resource_bundle": {
                    "resources": [
                        {
                            "task_id": "doc-1",
                            "type": "doc",
                            "content": "线性回归讲解。" * 20,
                        },
                        {
                            "task_id": "quiz-1",
                            "type": "quiz",
                            "content": "题目：什么是线性回归？答案：监督学习模型。" * 10,
                        },
                    ]
                }
            }
        }

    report = await EvalRunner(orchestrator=fake_orchestrator, judge=RuleJudge()).run(
        [case],
        strategy="coverage",
    )

    assert report.results[0].resource_coverage == 0.6667
    assert report.avg_resource_coverage == 0.6667


def test_comparison_report_includes_resource_coverage():
    from reflexlearn.eval.report import comparison_to_markdown
    from reflexlearn.eval.schemas import EvalReport

    text = comparison_to_markdown(
        [
            EvalReport(
                strategy="full-smoke",
                total_cases=1,
                task_completion_rate=1.0,
                avg_resource_coverage=1.0,
                avg_overall=0.8,
            ),
            EvalReport(
                strategy="single_agent_baseline",
                total_cases=1,
                task_completion_rate=1.0,
                avg_resource_coverage=0.3333,
                avg_overall=0.6,
            ),
        ]
    )

    assert "resource_coverage" in text
    assert "| single_agent_baseline |" in text
    assert "33.3%" in text


def test_run_eval_script_accepts_tag_filter():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    script = (root / "scripts" / "jobs" / "run_eval.py").read_text(encoding="utf-8")

    assert "--tags" in script
    assert "select_eval_cases" in script


def test_default_eval_strategies_include_controlled_ablation_profiles():
    from reflexlearn.eval.strategies import default_eval_strategies

    profiles = {item.name: item for item in default_eval_strategies()}

    assert profiles["controlled_rag"].env["EVAL_BASELINE"] == "controlled_rag"
    assert profiles["controlled_reflexion"].env["EVAL_BASELINE"] == "controlled_reflexion"
    assert profiles["controlled_rag"].env["ENABLE_RAG"] == "false"
    assert profiles["controlled_reflexion"].env["ENABLE_REFLEXION"] == "false"


def test_default_eval_strategies_include_metacognition_ablation_profiles():
    from reflexlearn.eval.strategies import default_eval_strategies

    profiles = {item.name: item for item in default_eval_strategies()}

    assert profiles["metacognition_off"].env["ENABLE_METACOGNITION"] == "false"
    assert profiles["metacognition_on"].env["ENABLE_METACOGNITION"] == "true"
    assert profiles["metacognition_on"].env["MAX_SELF_REFINE"] == "1"
    assert profiles["metacognition_real_on"].env["ENABLE_METACOGNITION"] == "true"
    assert profiles["metacognition_real_on"].env["ENABLE_LLM_GENERATION"] == "false"
    assert profiles["metacognition_real_on"].env["METACOGNITION_MAX_REVIEWS"] == "1"
    assert "OPENAI_COMPAT_API_KEY" not in profiles["metacognition_real_on"].env
    assert "DEEPSEEK_API_KEY" not in profiles["metacognition_real_on"].env


@pytest.mark.asyncio
async def test_controlled_rag_baseline_improves_rag_required_case():
    from reflexlearn.eval.baselines import controlled_rag_baseline, single_agent_baseline
    from reflexlearn.eval.dataset import select_eval_cases
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner

    case = select_eval_cases(tags=["ablation", "rag_required"])[0]

    rag_report = await EvalRunner(
        orchestrator=controlled_rag_baseline,
        judge=RuleJudge(),
    ).run([case], strategy="controlled_rag")
    baseline_report = await EvalRunner(
        orchestrator=single_agent_baseline,
        judge=RuleJudge(),
    ).run([case], strategy="single_agent_baseline")

    assert rag_report.avg_correctness == 1.0
    assert rag_report.avg_overall > baseline_report.avg_overall
    assert rag_report.avg_resource_coverage == 1.0


@pytest.mark.asyncio
async def test_controlled_reflexion_baseline_improves_reflexion_required_case():
    from reflexlearn.eval.baselines import controlled_reflexion_baseline, single_agent_baseline
    from reflexlearn.eval.dataset import select_eval_cases
    from reflexlearn.eval.judge import RuleJudge
    from reflexlearn.eval.runner import EvalRunner

    case = select_eval_cases(tags=["ablation", "reflexion_required"])[0]

    reflexion_report = await EvalRunner(
        orchestrator=controlled_reflexion_baseline,
        judge=RuleJudge(),
    ).run([case], strategy="controlled_reflexion")
    baseline_report = await EvalRunner(
        orchestrator=single_agent_baseline,
        judge=RuleJudge(),
    ).run([case], strategy="single_agent_baseline")

    assert reflexion_report.avg_correctness == 1.0
    assert reflexion_report.avg_overall > baseline_report.avg_overall
    assert reflexion_report.avg_resource_coverage == 1.0
