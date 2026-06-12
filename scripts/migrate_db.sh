#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "migrate_db"
  "$(python_cmd)" scripts/init/init_db.py
} 2>&1 | tee -a "$LOG_DIR/migrate_db.log"
