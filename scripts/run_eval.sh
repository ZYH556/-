#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "run_eval"
  if [[ ! -f "$PROJECT_ROOT/scripts/run_eval.py" ]]; then
    echo "scripts/run_eval.py is not implemented yet."
    exit 2
  fi
  "$(python_cmd)" scripts/run_eval.py "$@"
} 2>&1 | tee -a "$LOG_DIR/run_eval.log"
