#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "test_unit"
  if [[ "$#" -gt 0 ]]; then
    "$(python_cmd)" -m pytest "$@" -q
  else
    "$(python_cmd)" -m pytest tests/unit -q
  fi
} 2>&1 | tee -a "$LOG_DIR/test_unit.log"
