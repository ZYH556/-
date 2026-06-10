from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reflexlearn.eval.baselines import (
    controlled_rag_baseline,
    controlled_reflexion_baseline,
    single_agent_baseline,
)
from reflexlearn.eval.dataset import select_eval_cases
from reflexlearn.eval.judge import LLMJudge
from reflexlearn.eval.report import comparison_to_markdown, report_to_markdown
from reflexlearn.eval.runner import EvalRunner
from reflexlearn.eval.schemas import EvalCase, EvalReport, EvalResult, EvalTraceEvent
from reflexlearn.eval.strategies import EvalStrategy, default_eval_strategies, run_strategy_suite
from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.orchestration.graph import run_session
from reflexlearn.common.logging import configure_logging


async def _orchestrator(case: EvalCase):
    async for event in run_session(
        case.goal,
        user_id="eval",
        session_id="",
        resource_type_hints=case.expected_resource_types,
    ):
        yield event
        if "assemble" in event:
            break


async def _run(args: argparse.Namespace) -> int:
    configure_logging()
    _apply_smoke_defaults()
    _apply_real_mode(args.real)
    cases = select_eval_cases(tags=_parse_tags(args.tags), max_cases=args.max_cases)
    if not cases:
        print("no eval cases matched", file=sys.stderr)
        return 2
    if args.compare:
        profiles = _select_profiles(args.strategies, real=args.real)
        reports = await _run_profiles_with_preflight(
            cases,
            profiles=profiles,
            timeout=args.timeout,
            real=args.real,
        )
        comparison_json = ROOT / "logs" / "eval_comparison.json"
        comparison_md = ROOT / "logs" / "eval_comparison.md"
        comparison_json.parent.mkdir(parents=True, exist_ok=True)
        comparison_json.write_text(
            json.dumps([r.model_dump(mode="json") for r in reports], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        comparison_md.write_text(comparison_to_markdown(reports), encoding="utf-8")
        print(json.dumps([r.model_dump(mode="json") for r in reports], ensure_ascii=False, indent=2))
        print(f"eval_comparison={comparison_json}")
        print(f"eval_comparison_md={comparison_md}")
        return 0 if all(r.task_completion_rate > 0 for r in reports) else 1

    runner = EvalRunner(
        orchestrator=_orchestrator,
        judge=LLMJudge(LLMGateway()),
        per_case_timeout_s=args.timeout,
    )
    report = await runner.run(cases, strategy=args.strategy)
    json_out = ROOT / "logs" / "eval_report.json"
    md_out = ROOT / "logs" / "eval_report.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    md_out.write_text(report_to_markdown(report), encoding="utf-8")
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print(f"eval_report={json_out}")
    print(f"eval_report_md={md_out}")
    return 0 if report.task_completion_rate > 0 else 1


def _make_runner(profile: EvalStrategy, timeout: float) -> EvalRunner:
    orchestrator = _baseline_orchestrator(profile.env.get("EVAL_BASELINE", ""))
    return EvalRunner(
        orchestrator=orchestrator,
        judge=LLMJudge(LLMGateway()),
        per_case_timeout_s=timeout,
    )


def _baseline_orchestrator(name: str):
    if name == "single_agent":
        return single_agent_baseline
    if name == "controlled_rag":
        return controlled_rag_baseline
    if name == "controlled_reflexion":
        return controlled_reflexion_baseline
    return _orchestrator


async def _run_profiles_with_preflight(
    cases: list[EvalCase],
    *,
    profiles: list[EvalStrategy],
    timeout: float,
    real: bool,
) -> list[EvalReport]:
    reports: list[EvalReport] = []
    rag_ready: tuple[bool, str] | None = None
    for profile in profiles:
        if real and _rag_preflight_enabled() and _profile_requires_rag(profile):
            if rag_ready is None:
                rag_ready = await _check_rag_ready()
            ready, reason = rag_ready
            if not ready:
                reports.append(_blocked_report(cases, profile.name, reason))
                continue
        reports.extend(
            await run_strategy_suite(
                cases,
                profiles=[profile],
                runner_factory=lambda item: _make_runner(item, timeout),
            )
        )
    return reports


def _profile_requires_rag(profile: EvalStrategy) -> bool:
    return profile.env.get("ENABLE_RAG", "").lower() == "true"


def _rag_preflight_enabled() -> bool:
    return os.getenv("EVAL_RAG_PREFLIGHT", "true").lower() not in {"0", "false", "no"}


async def _check_rag_ready() -> tuple[bool, str]:
    import httpx

    from reflexlearn.common.config import get_settings

    settings = get_settings()
    url = f"{settings.qdrant_url.rstrip('/')}/collections/{settings.knowledge_collection}"
    timeout_s = float(getattr(settings, "rag_route_timeout_s", 3.0))
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.get(url)
        if response.status_code == 200:
            return True, "rag_ready"
        return False, f"qdrant collection unavailable: HTTP {response.status_code} {url}"
    except Exception as exc:
        return False, f"qdrant unavailable: {type(exc).__name__} {url}"


def _blocked_report(cases: list[EvalCase], strategy: str, reason: str) -> EvalReport:
    return EvalReport(
        strategy=strategy,
        total_cases=len(cases),
        task_completion_rate=0.0,
        results=[
            EvalResult(
                case_id=case.case_id,
                strategy=strategy,
                task_completed=False,
                error="rag_preflight_failed",
                last_event="preflight",
                event_trace=[
                    EvalTraceEvent(
                        sequence=1,
                        node="preflight",
                        elapsed_ms=0,
                        keys=["rag"],
                        summary=reason,
                    )
                ],
            )
            for case in cases
        ],
    )


def _select_profiles(raw: str, *, real: bool = False) -> list[EvalStrategy]:
    wanted = [item.strip() for item in raw.split(",") if item.strip()]
    profiles = default_eval_strategies()
    if not wanted:
        defaults = _default_profile_names(real=real)
        return [profile for profile in profiles if profile.name in defaults]
    selected = [profile for profile in profiles if profile.name in wanted]
    missing = sorted(set(wanted) - {profile.name for profile in selected})
    if missing:
        raise SystemExit(f"unknown eval strategies: {', '.join(missing)}")
    return selected


def _default_profile_names(*, real: bool) -> set[str]:
    if real:
        return {"real_full", "real_no_rag", "real_no_reflexion", "single_agent_baseline"}
    return {
        "full-smoke",
        "no_rag",
        "no_reflexion",
        "controlled_rag",
        "controlled_reflexion",
        "single_agent_baseline",
    }


def _parse_tags(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def _apply_smoke_defaults() -> None:
    # 默认先跑稳定 smoke：避免真实 embedding/reranker 在演示机上拖慢 M5 评测。
    os.environ.setdefault("ENABLE_RAG", "false")
    os.environ.setdefault("ENABLE_MULTI_TURN", "false")


def _apply_real_mode(enabled: bool) -> None:
    if not enabled:
        return
    os.environ["ENABLE_RAG"] = "true"
    os.environ["ENABLE_MULTI_TURN"] = "true"
    os.environ["ENABLE_REFLEXION"] = "true"
    os.environ.setdefault("ENABLE_LLM_PROFILE", "false")
    os.environ.setdefault("ENABLE_LLM_QUALITY_CHECK", "false")
    os.environ.setdefault("ENABLE_LLM_PLANNER", "false")
    os.environ.setdefault("EVAL_FORCE_COLLAB_MODE", "central")
    os.environ.setdefault("EVAL_SKIP_PATH_PLAN", "true")
    try:
        from reflexlearn.common.config import get_settings

        get_settings.cache_clear()
    except Exception:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ReflexLearn M5 eval harness.")
    parser.add_argument("--max-cases", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--strategy", default="full-smoke")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--strategies", default="")
    parser.add_argument("--tags", default="", help="Comma-separated eval case tags; all tags must match.")
    parser.add_argument("--real", action="store_true", help="Enable real RAG, multi-turn, and Reflexion by default.")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
