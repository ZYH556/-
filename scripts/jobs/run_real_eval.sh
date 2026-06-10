#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults
export ENABLE_GENERATOR_DIAGNOSTICS="${ENABLE_GENERATOR_DIAGNOSTICS:-true}"
export EVAL_FORCE_COLLAB_MODE="${EVAL_FORCE_COLLAB_MODE:-central}"
export ENABLE_LLM_PROFILE="${ENABLE_LLM_PROFILE:-false}"
export ENABLE_LLM_QUALITY_CHECK="${ENABLE_LLM_QUALITY_CHECK:-false}"
export MAX_REACT_STEPS="${MAX_REACT_STEPS:-1}"
export LLM_REQUEST_TIMEOUT_S="${LLM_REQUEST_TIMEOUT_S:-15}"
export EVAL_SKIP_PATH_PLAN="${EVAL_SKIP_PATH_PLAN:-true}"
export ENABLE_LLM_PLANNER="${ENABLE_LLM_PLANNER:-false}"
export ENABLE_RERANK="${ENABLE_RERANK:-false}"

{
  log_header "run_real_eval"
  timeout_s="${REAL_EVAL_TIMEOUT:-180}"
  max_cases="${REAL_EVAL_MAX_CASES:-0}"
  tags="${REAL_EVAL_TAGS:-ablation}"
  strategies="${REAL_EVAL_STRATEGIES:-real_full,real_no_rag,real_no_reflexion,single_agent_baseline}"
  if [[ "$#" -gt 0 ]]; then
    bash "$SCRIPTS_ROOT/run_eval.sh" --real --compare "$@"
    exit 0
  fi
  bash "$SCRIPTS_ROOT/run_eval.sh" \
    --real \
    --compare \
    --tags "$tags" \
    --strategies "$strategies" \
    --max-cases "$max_cases" \
    --timeout "$timeout_s"
} 2>&1 | tee -a "$LOG_DIR/run_real_eval.log"
