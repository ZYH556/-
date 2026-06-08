#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "init_all"
  "$(python_cmd)" scripts/init_db.py
  "$(python_cmd)" scripts/init_qdrant.py
  "$(python_cmd)" scripts/ingest_graph.py
} 2>&1 | tee -a "$LOG_DIR/init_all.log"
