from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable

from reflexlearn.common.config import get_settings
from reflexlearn.eval.judge import RuleJudge
from reflexlearn.eval.schemas import EvalCase, EvalReport, EvalResource, EvalResult, EvalTraceEvent, JudgeScore

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
        trace: list[EvalTraceEvent] = []
        try:
            events = await asyncio.wait_for(
                self._collect_events(case, trace, start),
                timeout=self.per_case_timeout_s,
            )
        except TimeoutError:
            return EvalResult(
                case_id=case.case_id,
                strategy=strategy,
                task_completed=False,
                latency_ms=_elapsed_ms(start),
                error="timeout",
                last_event=_last_event(trace),
                event_trace=trace,
            )
        except Exception as exc:
            return EvalResult(
                case_id=case.case_id,
                strategy=strategy,
                task_completed=False,
                latency_ms=_elapsed_ms(start),
                error=type(exc).__name__,
                last_event=_last_event(trace),
                event_trace=trace,
            )

        resources = _extract_resources(events)
        scores, judge_error = await self._evaluate_resources(case, resources, start)
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
            error=judge_error,
            last_event=_last_event(trace),
            event_trace=trace,
        )

    async def _collect_events(
        self,
        case: EvalCase,
        trace: list[EvalTraceEvent],
        start: float,
    ) -> list[dict]:
        events: list[dict] = []
        async for event in self.orchestrator(case):
            events.append(event)
            _record_trace(trace, event, start)
        return events

    async def _evaluate_resources(
        self,
        case: EvalCase,
        resources: list[EvalResource],
        start: float,
    ) -> tuple[list[JudgeScore], str]:
        scores = []
        fallback = RuleJudge()
        error = ""
        max_resources = max(0, int(get_settings().eval_judge_max_resources))
        judged_resources = _judge_candidates(resources, max_resources=max_resources)
        for res in judged_resources:
            remaining = self.per_case_timeout_s - (time.time() - start)
            if remaining <= 0:
                scores.append(await fallback.evaluate(case=case, resource=res, reference=""))
                error = error or "judge_timeout_rule_fallback"
                continue
            try:
                score = await asyncio.wait_for(
                    self.judge.evaluate(case=case, resource=res, reference=""),
                    timeout=remaining,
                )
            except TimeoutError:
                score = await fallback.evaluate(case=case, resource=res, reference="")
                error = error or "judge_timeout_rule_fallback"
            scores.append(score)
        return scores, error


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


def _judge_candidates(resources: list[EvalResource], *, max_resources: int) -> list[EvalResource]:
    if max_resources <= 0:
        return resources
    priority = {"doc": 0, "quiz": 1, "code": 2, "reading": 3, "mindmap": 4, "video": 5}
    ranked = sorted(
        enumerate(resources),
        key=lambda item: (priority.get(item[1].type, 99), item[0]),
    )
    return [resource for _, resource in ranked[:max_resources]]


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


def _record_trace(trace: list[EvalTraceEvent], event: dict, start: float) -> None:
    for node, output in event.items():
        keys = sorted(output.keys()) if isinstance(output, dict) else []
        trace.append(
            EvalTraceEvent(
                sequence=len(trace) + 1,
                node=str(node),
                elapsed_ms=_elapsed_ms(start),
                keys=[str(key) for key in keys],
                summary=_summarize_event(str(node), output),
            )
        )


def _last_event(trace: list[EvalTraceEvent]) -> str:
    return trace[-1].node if trace else ""


def _summarize_event(node: str, output) -> str:
    if not isinstance(output, dict):
        return ""
    if node == "planner":
        plan = output.get("plan")
        types = [str(item.get("type", "")) for item in plan] if isinstance(plan, list) else []
        return f"collab_mode={output.get('collab_mode', '')}; plan_types={','.join(types)}"
    if node in {"generate_resource", "pipeline"}:
        completed = output.get("completed")
        if not isinstance(completed, list):
            return ""
        statuses = [str(item.get("status", "")) for item in completed]
        types = [str(item.get("type", "")) for item in completed]
        return f"completed={len(completed)}; types={','.join(types)}; statuses={','.join(statuses)}"
    if node == "assemble":
        bundle = output.get("resource_bundle")
        if isinstance(bundle, dict):
            return f"resources={bundle.get('total', 0)}"
    if node == "metacognition":
        reviews = output.get("meta_reviews")
        review_count = len(reviews) if isinstance(reviews, list) else 0
        return f"reviews={review_count}; self_refine_count={output.get('self_refine_count', 0)}"
    return ""
