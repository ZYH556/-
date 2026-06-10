from __future__ import annotations

import time
from collections.abc import Sequence

from fastapi import FastAPI, Request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram
from prometheus_client.exposition import generate_latest

from reflexlearn.common.config import get_settings

REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS = Counter(
    "reflexlearn_http_requests_total",
    "Total HTTP requests handled by ReflexLearn API.",
    ["method", "path", "status_code"],
    registry=REGISTRY,
)
HTTP_LATENCY = Histogram(
    "reflexlearn_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ["method", "path"],
    registry=REGISTRY,
)
AGENT_NODE_RUNS = Counter(
    "reflexlearn_agent_node_runs_total",
    "LangGraph node executions.",
    ["node", "status"],
    registry=REGISTRY,
)
AGENT_NODE_LATENCY = Histogram(
    "reflexlearn_agent_node_duration_seconds",
    "LangGraph node execution duration in seconds.",
    ["node", "status"],
    registry=REGISTRY,
)
LLM_REQUESTS = Counter(
    "reflexlearn_llm_requests_total",
    "LLM gateway requests.",
    ["task_type", "model", "status"],
    registry=REGISTRY,
)
LLM_LATENCY = Histogram(
    "reflexlearn_llm_request_duration_seconds",
    "LLM gateway request duration in seconds.",
    ["task_type", "model", "status"],
    registry=REGISTRY,
)
LLM_TOKENS = Counter(
    "reflexlearn_llm_tokens_total",
    "LLM gateway token usage.",
    ["task_type", "model", "kind"],
    registry=REGISTRY,
)
RAG_ROUTES = Counter(
    "reflexlearn_rag_routes_total",
    "RAG route usage.",
    ["route", "status"],
    registry=REGISTRY,
)
RAG_RESULTS = Histogram(
    "reflexlearn_rag_result_count",
    "RAG result count per request.",
    ["status"],
    buckets=(0, 1, 2, 3, 5, 8, 13, 21),
    registry=REGISTRY,
)
MEMORY_RECALLS = Counter(
    "reflexlearn_memory_recalls_total",
    "Memory recall attempts.",
    ["mode", "status"],
    registry=REGISTRY,
)
MEMORY_RECALL_RESULTS = Histogram(
    "reflexlearn_memory_recall_result_count",
    "Memory recall result count per attempt.",
    ["mode", "status"],
    buckets=(0, 1, 2, 3, 5, 8, 13),
    registry=REGISTRY,
)
VIDEO_JOBS = Counter(
    "reflexlearn_video_jobs_total",
    "Video job status transitions.",
    ["status"],
    registry=REGISTRY,
)
DEGRADATIONS = Counter(
    "reflexlearn_degradations_total",
    "Graceful degradation events.",
    ["component", "reason"],
    registry=REGISTRY,
)
METACOGNITION_REVIEWS = Counter(
    "reflexlearn_metacognition_reviews_total",
    "Metacognition review attempts.",
    ["status"],
    registry=REGISTRY,
)
METACOGNITION_LATENCY = Histogram(
    "reflexlearn_metacognition_review_duration_seconds",
    "Metacognition review latency.",
    ["status"],
    registry=REGISTRY,
)


def metrics_content_type() -> str:
    return CONTENT_TYPE_LATEST


def export_metrics() -> bytes:
    return generate_latest(REGISTRY)


def _enabled() -> bool:
    return bool(getattr(get_settings(), "enable_metrics", True))


def _route_path(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or request.url.path


def record_http_request(method: str, path: str, status_code: int, duration_s: float) -> None:
    if not _enabled():
        return
    status = str(status_code)
    HTTP_REQUESTS.labels(method=method, path=path, status_code=status).inc()
    HTTP_LATENCY.labels(method=method, path=path).observe(max(duration_s, 0.0))


def observe_agent_node(node: str, status: str, duration_s: float) -> None:
    if not _enabled():
        return
    AGENT_NODE_RUNS.labels(node=node, status=status).inc()
    AGENT_NODE_LATENCY.labels(node=node, status=status).observe(max(duration_s, 0.0))


def observe_llm(
    *,
    task_type: str,
    model: str,
    status: str,
    latency_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    if not _enabled():
        return
    LLM_REQUESTS.labels(task_type=task_type, model=model, status=status).inc()
    LLM_LATENCY.labels(task_type=task_type, model=model, status=status).observe(
        max(latency_ms, 0) / 1000
    )
    if input_tokens:
        LLM_TOKENS.labels(task_type=task_type, model=model, kind="input").inc(input_tokens)
    if output_tokens:
        LLM_TOKENS.labels(task_type=task_type, model=model, kind="output").inc(output_tokens)


def observe_rag(*, routes_used: Sequence[str], result_count: int, status: str) -> None:
    if not _enabled():
        return
    for route in routes_used:
        RAG_ROUTES.labels(route=route, status=status).inc()
    RAG_RESULTS.labels(status=status).observe(max(result_count, 0))


def observe_memory_recall(*, mode: str, status: str, result_count: int) -> None:
    if not _enabled():
        return
    MEMORY_RECALLS.labels(mode=mode, status=status).inc()
    MEMORY_RECALL_RESULTS.labels(mode=mode, status=status).observe(max(result_count, 0))


def observe_video_job(status: str) -> None:
    if not _enabled():
        return
    VIDEO_JOBS.labels(status=status).inc()


def observe_degradation(component: str, reason: str) -> None:
    if not _enabled():
        return
    DEGRADATIONS.labels(component=component, reason=reason).inc()


def observe_metacognition(*, status: str, latency_ms: int) -> None:
    if not _enabled():
        return
    METACOGNITION_REVIEWS.labels(status=status).inc()
    METACOGNITION_LATENCY.labels(status=status).observe(max(latency_ms, 0) / 1000)


def instrument_app(app: FastAPI) -> None:
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            if request.url.path != "/metrics":
                record_http_request(
                    request.method,
                    _route_path(request),
                    status_code,
                    time.perf_counter() - start,
                )
