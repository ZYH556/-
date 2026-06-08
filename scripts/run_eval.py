from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# 默认先跑稳定 smoke：避免真实 embedding/reranker 在演示机上拖慢 M5 评测。
os.environ.setdefault("ENABLE_RAG", "false")
os.environ.setdefault("ENABLE_MULTI_TURN", "false")

ROOT = Path(__file__).resolve().parents[1]
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
from reflexlearn.eval.schemas import EvalCase
from reflexlearn.eval.strategies import EvalStrategy, default_eval_strategies, run_strategy_suite
from reflexlearn.llm_gateway.gateway import LLMGateway
from reflexlearn.orchestration.graph import run_session


async def _orchestrator(case: EvalCase):
    async for event in run_session(case.goal, user_id="eval", session_id=""):
        yield event


async def _run(args: argparse.Namespace) -> int:
    cases = select_eval_cases(tags=_parse_tags(args.tags), max_cases=args.max_cases)
    if not cases:
        print("no eval cases matched", file=sys.stderr)
        return 2
    if args.compare:
        profiles = _select_profiles(args.strategies)
        reports = await run_strategy_suite(
            cases,
            profiles=profiles,
            runner_factory=lambda profile: _make_runner(profile, args.timeout),
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


def _select_profiles(raw: str) -> list[EvalStrategy]:
    wanted = [item.strip() for item in raw.split(",") if item.strip()]
    profiles = default_eval_strategies()
    if not wanted:
        return profiles
    selected = [profile for profile in profiles if profile.name in wanted]
    missing = sorted(set(wanted) - {profile.name for profile in selected})
    if missing:
        raise SystemExit(f"unknown eval strategies: {', '.join(missing)}")
    return selected


def _parse_tags(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ReflexLearn M5 eval harness.")
    parser.add_argument("--max-cases", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument("--strategy", default="full-smoke")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--strategies", default="")
    parser.add_argument("--tags", default="", help="Comma-separated eval case tags; all tags must match.")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
