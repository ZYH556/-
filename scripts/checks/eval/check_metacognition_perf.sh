#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "check_metacognition_perf"
  bash "$SCRIPTS_ROOT/run_eval.sh" --compare \
    --tags ablation,reflexion_required \
    --strategies metacognition_real_off,metacognition_real_on \
    --max-cases 1 \
    --timeout 60

  "$(python_cmd)" - <<'PY'
import json
from pathlib import Path

report_path = Path("logs/eval_comparison.json")
if not report_path.exists():
    raise SystemExit("eval_comparison.json missing")

reports = {item["strategy"]: item for item in json.loads(report_path.read_text(encoding="utf-8"))}
off = reports.get("metacognition_real_off")
on = reports.get("metacognition_real_on")
if not off or not on:
    raise SystemExit("metacognition reports missing")

result = on["results"][0]
trace = result.get("event_trace", [])
nodes = [item.get("node") for item in trace]
if "metacognition" not in nodes:
    raise SystemExit("metacognition node missing from trace")
if result.get("error"):
    raise SystemExit(f"metacognition_on error={result.get('error')}")
if int(result.get("latency_ms", 999999)) > 45000:
    raise SystemExit(f"metacognition_on latency too high: {result.get('latency_ms')}ms")

metas = [item for item in trace if item.get("node") == "metacognition"]
if len(metas) > 1:
    raise SystemExit(f"metacognition ran too many times: {len(metas)}")
if "self_refine_count=1" not in (metas[0].get("summary") or ""):
    raise SystemExit(f"self_refine_count not 1: {metas[0].get('summary')}")

scores = [score for r in on["results"] for score in r.get("resource_scores", [])]
if not scores:
    raise SystemExit("metacognition_on has no judge scores")
if any(str(score.get("reasoning", "")).startswith("rule:") for score in scores):
    raise SystemExit("judge degraded to rule fallback")

if float(on.get("avg_overall", 0.0)) < float(off.get("avg_overall", 0.0)) - 0.03:
    raise SystemExit(
        f"overall regression too large: off={off.get('avg_overall')} on={on.get('avg_overall')}"
    )

print(
    "[OK] metacognition perf "
    f"latency_ms={result.get('latency_ms')} "
    f"off={off.get('avg_overall')} on={on.get('avg_overall')}"
)
PY
} 2>&1 | tee -a "$LOG_DIR/check_metacognition_perf.log"
