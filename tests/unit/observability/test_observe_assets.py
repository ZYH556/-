from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]


def test_grafana_provisioning_files_define_prometheus_dashboard():
    datasource = ROOT / "deploy/grafana/provisioning/datasources/prometheus.yml"
    dashboards = ROOT / "deploy/grafana/provisioning/dashboards/dashboard.yml"
    dashboard = ROOT / "deploy/grafana/dashboards/reflexlearn.json"

    assert datasource.exists()
    assert dashboards.exists()
    assert dashboard.exists()

    datasource_data = yaml.safe_load(datasource.read_text(encoding="utf-8"))
    assert datasource_data["datasources"][0]["name"] == "Prometheus"
    assert datasource_data["datasources"][0]["url"] == "http://prometheus:9090"

    dashboards_data = yaml.safe_load(dashboards.read_text(encoding="utf-8"))
    provider = dashboards_data["providers"][0]
    assert provider["name"] == "reflexlearn"
    assert provider["options"]["path"] == "/var/lib/grafana/dashboards"

    dashboard_data = json.loads(dashboard.read_text(encoding="utf-8"))
    assert dashboard_data["title"] == "ReflexLearn Observability"
    panel_text = json.dumps(dashboard_data, ensure_ascii=False)
    for metric in [
        "reflexlearn_http_requests_total",
        "reflexlearn_http_request_duration_seconds",
        "reflexlearn_agent_node_duration_seconds",
        "reflexlearn_llm_tokens_total",
        "reflexlearn_degradations_total",
    ]:
        assert metric in panel_text


def test_docker_compose_mounts_grafana_provisioning():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    grafana = compose["services"]["grafana"]
    volumes = grafana.get("volumes", [])

    assert "./deploy/grafana/provisioning:/etc/grafana/provisioning" in volumes
    assert "./deploy/grafana/dashboards:/var/lib/grafana/dashboards" in volumes


def test_observe_scripts_have_logging_contract_and_metrics_checks():
    scripts = ROOT / "scripts"
    implementations = {
        "start_observe.sh": scripts / "ops" / "start_observe.sh",
        "check_observe.sh": scripts / "checks" / "infra" / "check_observe.sh",
        "stop_observe.sh": scripts / "ops" / "stop_observe.sh",
    }

    for name, impl in implementations.items():
        wrapper_text = (scripts / name).read_text(encoding="utf-8")
        text = impl.read_text(encoding="utf-8")
        assert f'exec "$SCRIPT_DIR/' in wrapper_text
        assert 'source "$SCRIPTS_ROOT/_lib.sh"' in text
        assert "ensure_logs" in text
        assert 'tee -a "$LOG_DIR/' in text

    start_text = implementations["start_observe.sh"].read_text(encoding="utf-8")
    check_text = implementations["check_observe.sh"].read_text(encoding="utf-8")
    stop_text = implementations["stop_observe.sh"].read_text(encoding="utf-8")

    assert "--profile observe up -d" in start_text
    assert "--profile observe down" in stop_text
    assert "/metrics" in check_text
    assert "reflexlearn_http_requests_total" in check_text
    assert "http://127.0.0.1:${API_PORT}" in check_text
