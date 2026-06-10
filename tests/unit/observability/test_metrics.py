from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reflexlearn.api.app import create_app
from reflexlearn.orchestration.harness import harness_guard


def _metrics_text() -> str:
    from reflexlearn.observability.metrics import export_metrics

    return export_metrics().decode("utf-8")


def test_metrics_endpoint_records_http_requests():
    client = TestClient(create_app())

    health = client.get("/api/health")
    metrics = client.get("/metrics")

    assert health.status_code == 200
    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    body = metrics.text
    assert "reflexlearn_http_requests_total" in body
    assert 'path="/api/health"' in body
    assert 'status_code="200"' in body


@pytest.mark.asyncio
async def test_harness_guard_records_agent_node_metrics():
    async def demo_node(state):
        return {"ok": True}

    wrapped = harness_guard(demo_node)
    result = await wrapped({"iteration": 0, "token_used": 0})

    assert result == {"ok": True}
    body = _metrics_text()
    assert "reflexlearn_agent_node_runs_total" in body
    assert 'node="demo_node"' in body
    assert 'status="ok"' in body


def test_llm_rag_and_video_metrics_are_exported():
    from reflexlearn.observability.metrics import (
        observe_llm,
        observe_memory_recall,
        observe_rag,
        observe_video_job,
    )

    observe_llm(
        task_type="judgment",
        model="unit-model",
        status="ok",
        latency_ms=123,
        input_tokens=11,
        output_tokens=7,
    )
    observe_rag(routes_used=["semantic", "keyword"], result_count=3, status="ok")
    observe_memory_recall(mode="semantic", status="ok", result_count=2)
    observe_video_job("degraded")

    body = _metrics_text()
    assert "reflexlearn_llm_requests_total" in body
    assert 'task_type="judgment"' in body
    assert 'model="unit-model"' in body
    assert "reflexlearn_llm_tokens_total" in body
    assert 'kind="input"' in body
    assert 'kind="output"' in body
    assert "reflexlearn_rag_routes_total" in body
    assert 'route="semantic"' in body
    assert 'route="keyword"' in body
    assert "reflexlearn_memory_recalls_total" in body
    assert 'mode="semantic"' in body
    assert "reflexlearn_memory_recall_result_count" in body
    assert "reflexlearn_video_jobs_total" in body
    assert 'status="degraded"' in body


def test_metrics_observe_functions_respect_disabled_switch(monkeypatch):
    from reflexlearn.observability import metrics

    class _Settings:
        enable_metrics = False

    monkeypatch.setattr(metrics, "get_settings", lambda: _Settings())
    metrics.observe_degradation("unit_disabled_component", "unit_reason")

    body = _metrics_text()
    assert "unit_disabled_component" not in body


def test_security_smoke_checks_metrics_endpoint():
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    text = (root / "scripts" / "checks" / "api" / "check_api_security.sh").read_text(encoding="utf-8")

    assert "check_metrics" in text
    assert 'f"{API_ROOT}/metrics"' in text
    assert "reflexlearn_http_requests_total" in text
