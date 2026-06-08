#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root

{
  log_header "start_bigdata"
  docker compose --profile bigdata up -d
  docker compose --profile bigdata ps
} 2>&1 | tee -a "$LOG_DIR/start_bigdata.log"
