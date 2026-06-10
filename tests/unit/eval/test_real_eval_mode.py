from __future__ import annotations

from pathlib import Path
import importlib.util


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_real_eval_strategies_enable_external_dependencies():
    from reflexlearn.eval.strategies import default_eval_strategies

    profiles = {item.name: item for item in default_eval_strategies()}

    assert {"real_full", "real_no_rag", "real_no_reflexion"}.issubset(profiles)
    assert profiles["real_full"].env == {
        "ENABLE_RAG": "true",
        "ENABLE_MULTI_TURN": "true",
        "ENABLE_REFLEXION": "true",
    }
    assert profiles["real_no_rag"].env["ENABLE_RAG"] == "false"
    assert profiles["real_no_rag"].env["ENABLE_REFLEXION"] == "true"
    assert profiles["real_no_reflexion"].env["ENABLE_RAG"] == "true"
    assert profiles["real_no_reflexion"].env["ENABLE_REFLEXION"] == "false"


def test_report_markdown_marks_judge_source():
    from reflexlearn.eval.report import report_to_markdown
    from reflexlearn.eval.schemas import EvalReport, EvalResult, JudgeScore

    rule_report = EvalReport(
        strategy="unit",
        total_cases=1,
        task_completion_rate=1.0,
        results=[
            EvalResult(
                case_id="ml-001",
                strategy="unit",
                task_completed=True,
                resource_scores=[
                    JudgeScore(overall=0.8, reasoning="rule: deterministic fallback"),
                ],
            )
        ],
    )
    llm_report = EvalReport(
        strategy="unit",
        total_cases=1,
        task_completion_rate=1.0,
        results=[
            EvalResult(
                case_id="ml-001",
                strategy="unit",
                task_completed=True,
                resource_scores=[
                    JudgeScore(overall=0.8, reasoning="llm judge ok"),
                ],
            )
        ],
    )

    assert "Judge 来源：规则降级" in report_to_markdown(rule_report)
    assert "Judge 来源：LLM 或混合" in report_to_markdown(llm_report)


def test_comparison_markdown_marks_judge_source():
    from reflexlearn.eval.report import comparison_to_markdown
    from reflexlearn.eval.schemas import EvalReport, EvalResult, JudgeScore

    text = comparison_to_markdown(
        [
            EvalReport(
                strategy="rule",
                total_cases=1,
                task_completion_rate=1.0,
                results=[
                    EvalResult(
                        case_id="ml-001",
                        strategy="rule",
                        task_completed=True,
                        resource_scores=[JudgeScore(overall=0.8, reasoning="rule: fallback")],
                    )
                ],
            ),
            EvalReport(
                strategy="llm",
                total_cases=1,
                task_completion_rate=1.0,
                results=[
                    EvalResult(
                        case_id="ml-001",
                        strategy="llm",
                        task_completed=True,
                        resource_scores=[JudgeScore(overall=0.8, reasoning="llm ok")],
                    )
                ],
            ),
        ]
    )

    assert "Judge 来源" in text
    assert "| rule |" in text
    assert "规则降级" in text
    assert "LLM 或混合" in text


def test_run_real_eval_script_contract():
    root = _project_root()
    shell = root / "scripts" / "run_real_eval.sh"
    impl = root / "scripts" / "jobs" / "run_real_eval.sh"

    wrapper_text = shell.read_text(encoding="utf-8")
    text = impl.read_text(encoding="utf-8")

    assert 'source "$SCRIPT_DIR/_lib.sh"' in wrapper_text
    assert 'exec "$SCRIPT_DIR/jobs/run_real_eval.sh" "$@"' in wrapper_text
    assert 'source "$SCRIPTS_ROOT/_lib.sh"' in text
    assert "ensure_logs" in text
    assert "use_python_defaults" in text
    assert "run_real_eval" in text
    assert "--real" in text
    assert 'ENABLE_RERANK="${ENABLE_RERANK:-false}"' in text
    assert 'REAL_EVAL_TIMEOUT:-180' in text
    assert "real_full,real_no_rag,real_no_reflexion,single_agent_baseline" in text
    assert 'if [[ "$#" -gt 0 ]]' in text
    assert 'bash "$SCRIPTS_ROOT/run_eval.sh" --real --compare "$@"' in text
    assert 'tee -a "$LOG_DIR/run_real_eval.log"' in text


def test_run_eval_profile_selection_keeps_smoke_default():
    module = _load_run_eval_module()

    smoke = [item.name for item in module._select_profiles("", real=False)]
    real = [item.name for item in module._select_profiles("", real=True)]

    assert smoke == [
        "full-smoke",
        "no_rag",
        "no_reflexion",
        "controlled_rag",
        "controlled_reflexion",
        "single_agent_baseline",
    ]
    assert real == ["real_full", "real_no_rag", "real_no_reflexion", "single_agent_baseline"]


def test_run_eval_orchestrator_stops_after_assemble():
    root = _project_root()
    script = (root / "scripts" / "jobs" / "run_eval.py").read_text(encoding="utf-8")

    assert 'resource_type_hints=case.expected_resource_types' in script
    assert 'if "assemble" in event' in script
    assert "break" in script


def test_loading_run_eval_module_does_not_mutate_eval_env(monkeypatch):
    import os

    monkeypatch.delenv("ENABLE_RAG", raising=False)
    monkeypatch.delenv("ENABLE_MULTI_TURN", raising=False)
    monkeypatch.delenv("ENABLE_REFLEXION", raising=False)

    _load_run_eval_module()

    assert "ENABLE_RAG" not in os.environ
    assert "ENABLE_MULTI_TURN" not in os.environ
    assert "ENABLE_REFLEXION" not in os.environ


def test_apply_real_mode_sets_eval_isolation_defaults(monkeypatch):
    import os

    module = _load_run_eval_module()
    from reflexlearn.common.config import get_settings

    keys = [
        "ENABLE_LLM_PROFILE",
        "ENABLE_LLM_QUALITY_CHECK",
        "ENABLE_LLM_PLANNER",
        "EVAL_FORCE_COLLAB_MODE",
        "EVAL_SKIP_PATH_PLAN",
    ]
    old_values = {key: os.environ.get(key) for key in keys}
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    try:
        module._apply_real_mode(True)

        assert os.environ["ENABLE_LLM_PROFILE"] == "false"
        assert os.environ["ENABLE_LLM_QUALITY_CHECK"] == "false"
        assert os.environ["ENABLE_LLM_PLANNER"] == "false"
        assert os.environ["EVAL_FORCE_COLLAB_MODE"] == "central"
        assert os.environ["EVAL_SKIP_PATH_PLAN"] == "true"
    finally:
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        get_settings.cache_clear()


def test_real_rag_profile_preflight_block_report():
    from reflexlearn.eval.dataset import default_eval_cases
    from reflexlearn.eval.strategies import EvalStrategy

    module = _load_run_eval_module()
    profile = EvalStrategy(
        name="real_full",
        description="unit",
        env={"ENABLE_RAG": "true"},
    )
    cases = default_eval_cases()[:1]

    assert module._profile_requires_rag(profile) is True
    report = module._blocked_report(cases, "real_full", "qdrant unavailable")

    assert report.strategy == "real_full"
    assert report.task_completion_rate == 0.0
    assert report.results[0].error == "rag_preflight_failed"
    assert report.results[0].last_event == "preflight"
    assert "qdrant unavailable" in report.results[0].event_trace[0].summary


def _load_run_eval_module():
    path = _project_root() / "scripts" / "jobs" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("run_eval_contract", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
