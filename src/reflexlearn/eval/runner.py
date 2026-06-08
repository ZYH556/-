from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable

from reflexlearn.eval.judge import RuleJudge
from reflexlearn.eval.schemas import EvalCase, EvalReport, EvalResource, EvalResult

Orchestrator = Callable[[EvalCase], AsyncIterator[dict]]


class EvalRunner:
    def __init__(
        self,
        *,
        orchestrator: Orchestrator,
        judge: RuleJudge | None = None,
        per_case_timeout_s: float = 25.0,
    ):
        self.orchestrator = orchestrator
        self.judge = judge or RuleJudge()
        self.per_case_timeout_s = per_case_timeout_s

    async def run(self, cases: list[EvalCase], *, strategy: str = "full") -> EvalReport:
        results = [await self._run_case(case, strategy) for case in cases]
        return _aggregate(results, strategy)

    async def _run_case(self, case: EvalCase, strategy: str) -> EvalResult:
        start = time.time()
        try:
            events = await asyncio.wait_for(
                self._collect_events(case),
                timeout=self.per_case_timeout_s,
            )
        except TimeoutError:
            return EvalResult(
                case_id=case.case_id,
                strategy=strategy,
                task_completed=False,
                latency_ms=_elapsed_ms(start),
                error="timeout",
            )
        except Exception as exc:
            return EvalResult(
                case_id=case.case_id,
                strategy=strategy,
                task_completed=False,
                latency_ms=_elapsed_ms(start),
                error=type(exc).__name__,
            )

        resources = _extract_resources(events)
        scores = [
            await self.judge.evaluate(case=case, resource=res, reference="")
            for res in resources
        ]
        generated = [res.type for res in resources]
        matched_types = set(case.expected_resource_types).intersection(generated)
        resource_coverage = _resource_coverage(case.expected_resource_types, generated)
        task_completed = bool(resources) and bool(matched_types)
        return EvalResult(
            case_id=case.case_id,
            strategy=strategy,
            task_completed=task_completed,
            resource_types_generated=generated,
            resource_coverage=resource_coverage,
            resource_scores=scores,
            latency_ms=_elapsed_ms(start),
        )

    async def _collect_events(self, case: EvalCase) -> list[dict]:
        events: list[dict] = []
        async for event in self.orchestrator(case):
            events.append(event)
        return events


def _extract_resources(events: list[dict]) -> list[EvalResource]:
    resources: list[EvalResource] = []
    for event in events:
        for node_output in event.values():
            if not isinstance(node_output, dict):
                continue
            bundle = node_output.get("resource_bundle")
            if isinstance(bundle, dict) and isinstance(bundle.get("resources"), list):
                resources.extend(_coerce_resource(item) for item in bundle["resources"])
            if {"task_id", "type", "content"}.issubset(node_output.keys()):
                resources.append(_coerce_resource(node_output))
    return [res for res in resources if res.content.strip()]


def _coerce_resource(raw: dict) -> EvalResource:
    spec = raw.get("spec") if isinstance(raw.get("spec"), dict) else {}
    return EvalResource(
        task_id=str(raw.get("task_id") or "unknown"),
        type=str(raw.get("type") or "doc"),
        content=str(raw.get("content") or ""),
        difficulty=float(raw.get("difficulty") or spec.get("difficulty") or 0.5),
    )


def _aggregate(results: list[EvalResult], strategy: str) -> EvalReport:
    scores = [score for result in results for score in result.resource_scores]
    total = len(results)
    completed = sum(1 for result in results if result.task_completed)
    return EvalReport(
        strategy=strategy,
        total_cases=total,
        task_completion_rate=round(completed / total, 4) if total else 0.0,
        avg_resource_coverage=_avg([result.resource_coverage for result in results]),
        avg_correctness=_avg([score.correctness for score in scores]),
        avg_profile_match=_avg([score.profile_match for score in scores]),
        avg_completeness=_avg([score.completeness for score in scores]),
        avg_format_quality=_avg([score.format_quality for score in scores]),
        avg_overall=_avg([score.overall for score in scores]),
        results=results,
    )


def _avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _resource_coverage(expected: list[str], generated: list[str]) -> float:
    if not expected:
        return 1.0 if generated else 0.0
    matched = set(expected).intersection(generated)
    return round(len(matched) / len(set(expected)), 4)


def _elapsed_ms(start: float) -> int:
    return int((time.time() - start) * 1000)
