#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root

{
  log_header "start_observe"
  "$(docker_cmd)" compose --profile observe up -d
  "$(docker_cmd)" compose --profile observe ps
} 2>&1 | tee -a "$LOG_DIR/start_observe.log"
