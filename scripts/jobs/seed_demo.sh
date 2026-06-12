#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "seed_demo"
  LEGACY_LOG="$LOG_DIR/seed_demo_legacy.log"
  if "$(python_cmd)" scripts/jobs/data/seed_demo.py "$@" >"$LEGACY_LOG" 2>&1; then
    echo "legacy_seed -> ok"
  else
    echo "legacy_seed -> degraded (database unavailable or legacy seed failed; see $LEGACY_LOG)"
  fi
  "$(python_cmd)" -m reflexlearn.learning.seed_demo_cli "$@"
  echo "seed_demo -> ok"
} 2>&1 | tee -a "$LOG_DIR/seed_demo.log"
