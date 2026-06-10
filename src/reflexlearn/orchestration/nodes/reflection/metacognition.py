from __future__ import annotations

import asyncio
import json
import logging
import time

from pydantic import ValidationError
from langgraph.types import Send

from reflexlearn.common.config import get_settings
from reflexlearn.observability.metrics import observe_degradation, observe_metacognition
from reflexlearn.orchestration.schemas import MetaReview
from reflexlearn.orchestration.state import AgentState

logger = logging.getLogger(__name__)

_PROMPT = (
    "你是 ReflexLearn 的元认知审查节点。请快速评估学习资源是否需要一次 self-refine。"
    "如果资源是离线占位、降级内容、内容空泛，或未覆盖 expected_concepts，"
    "必须给 score < 0.7，并提供具体可执行的 refine_hint；否则 refine_hint 为空。"
    "只输出 JSON：score(0-1), issues, refine_hint, suggested_skill。"
)


async def metacognition_node(state: AgentState) -> dict:
    started = time.perf_counter()
    settings = get_settings()
    if not settings.enable_metacognition:
        return {"meta_reviews": state.get("meta_reviews", [])}
    if state.get("self_refine_count", 0) >= settings.max_self_refine:
        return {"meta_reviews": state.get("meta_reviews", [])}

    llm = state.get("_llm")
    if llm is None:
        return {"meta_reviews": state.get("meta_reviews", []) + [_degraded_review("llm_missing")]}

    reviews: list[dict] = []
    refine_hints: dict[str, MetaReview] = {}
    candidates = _review_candidates(state, max_reviews=settings.metacognition_max_reviews)
    for item in candidates:
        review, data = await _review_one(llm, state, item, settings=settings)
        reviews.append({**data, "task_id": item.get("task_id", "")})
        if review is None:
            continue
        if review.score < settings.metacognition_min_score and review.refine_hint.strip():
            refine_hints[item.get("task_id", "")] = review

    _log_node_done(started, candidates=len(candidates), reviews=len(reviews), refine=len(refine_hints))
    if not reviews:
        return {"meta_reviews": state.get("meta_reviews", [])}
    if not refine_hints:
        return {"meta_reviews": state.get("meta_reviews", []) + reviews}

    _mark_for_refine(state.get("completed", []), refine_hints)
    return {
        "plan": _plan_with_refine_hints(state.get("plan", []), refine_hints),
        "self_refine_count": state.get("self_refine_count", 0) + 1,
        "meta_reviews": state.get("meta_reviews", []) + reviews,
    }


def metacognition_route(state: AgentState):
    refine_tasks = [
        task for task in state.get("plan", [])
        if task.get("status") == "pending" and task.get("spec", {}).get("refine_hint")
    ]
    if not refine_tasks:
        return "assemble"
    return [Send("generate_resource", {**state, "_current_task": task}) for task in refine_tasks]


def _passed_resources(state: AgentState) -> list[dict]:
    return [
        item for item in state.get("completed", [])
        if item.get("status") == "passed" and not item.get("meta_reviewed")
    ]


def _review_candidates(state: AgentState, *, max_reviews: int) -> list[dict]:
    resources = _passed_resources(state)
    if not resources or max_reviews <= 0:
        return []

    def score(item: dict) -> tuple[int, int, int]:
        quality = item.get("quality_score")
        low_quality = 0 if isinstance(quality, (int, float)) and quality < 0.75 else 1
        doc_first = 0 if item.get("type") == "doc" else 1
        content_len = len(str(item.get("content", "")))
        return (low_quality, doc_first, content_len)

    return sorted(resources, key=score)[:max_reviews]


async def _review_one(llm, state: AgentState, resource: dict, *, settings) -> tuple[MetaReview | None, dict]:
    started = time.perf_counter()
    try:
        completion = await asyncio.wait_for(
            llm.complete(
                [
                    {"role": "system", "content": _PROMPT},
                    {
                        "role": "user",
                        "content": json.dumps(_review_payload(state, resource, settings), ensure_ascii=False),
                    },
                ],
                task_type="reasoning",
                schema=MetaReview,
                temperature=0.1,
            ),
            timeout=float(settings.metacognition_timeout_s),
        )
        review = MetaReview.model_validate_json(completion.text)
        data = {**review.model_dump(), "status": "ok", "duration_ms": _elapsed_ms(started)}
        observe_metacognition(status="ok", latency_ms=data["duration_ms"])
        return review, data
    except asyncio.TimeoutError:
        return None, _degraded_review("timeout", started=started)
    except (ValidationError, ValueError, json.JSONDecodeError, AttributeError):
        return None, _degraded_review("bad_json", started=started)
    except Exception as exc:
        return None, _degraded_review(type(exc).__name__, started=started)


def _review_payload(state: AgentState, resource: dict, settings) -> dict:
    task_id = resource.get("task_id", "")
    task = next((item for item in state.get("plan", []) if item.get("task_id") == task_id), {})
    spec = task.get("spec", {}) if isinstance(task, dict) else {}
    content = str(resource.get("content", ""))
    return {
        "learning_goal": state.get("learning_goal", ""),
        "resource_type": resource.get("type", ""),
        "title": resource.get("title") or resource.get("task_id", ""),
        "summary": content[: int(settings.metacognition_content_chars)],
        "previous_issues": spec.get("previous_issues", []) or resource.get("issues", []),
        "expected_concepts": spec.get("concept_ids", []),
    }


def _degraded_review(reason: str, *, started: float | None = None) -> dict:
    duration_ms = _elapsed_ms(started) if started is not None else 0
    observe_degradation("metacognition", reason)
    observe_metacognition(status=f"degraded_{reason}", latency_ms=duration_ms)
    return {
        "score": 1.0,
        "issues": [f"metacognition_degraded:{reason}"],
        "refine_hint": "",
        "suggested_skill": "",
        "status": "degraded",
        "reason": reason,
        "duration_ms": duration_ms,
    }


def _elapsed_ms(started: float | None) -> int:
    if started is None:
        return 0
    return int((time.perf_counter() - started) * 1000)


def _log_node_done(started: float, *, candidates: int, reviews: int, refine: int) -> None:
    logger.info(
        "metacognition_diag duration_ms=%s candidates=%s reviews=%s refine=%s",
        _elapsed_ms(started),
        candidates,
        reviews,
        refine,
    )


def _mark_for_refine(completed: list[dict], refine_hints: dict[str, MetaReview]) -> None:
    for item in completed:
        task_id = item.get("task_id", "")
        if task_id in refine_hints and item.get("status") == "passed":
            item["status"] = "needs_refine"
            item["meta_reviewed"] = True


def _plan_with_refine_hints(plan: list[dict], refine_hints: dict[str, MetaReview]) -> list[dict]:
    updated: list[dict] = []
    for task in plan:
        task_id = task.get("task_id", "")
        if task_id not in refine_hints:
            updated.append(task)
            continue
        review = refine_hints[task_id]
        spec = {
            **task.get("spec", {}),
            "refine_hint": review.refine_hint,
            "suggested_skill": review.suggested_skill,
        }
        updated.append({**task, "status": "pending", "spec": spec})
    return updated
