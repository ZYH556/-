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
  log_header "start_mcp"
  "$(python_cmd)" -m reflexlearn.mcp_tools.server
} 2>&1 | tee -a "$LOG_DIR/start_mcp.log"
