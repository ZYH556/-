#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root
use_local_network
FRONTEND_API_BASE="${1:-${NEXT_PUBLIC_API_BASE:-http://localhost:8000/api}}"
export NEXT_PUBLIC_API_BASE="$FRONTEND_API_BASE"

{
  log_header "build_frontend -> $NEXT_PUBLIC_API_BASE"
  cd "$PROJECT_ROOT/frontend"
  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe //C "set NEXT_PUBLIC_API_BASE=$FRONTEND_API_BASE&& npm run build"
  else
    npm run build
  fi
} 2>&1 | tee -a "$LOG_DIR/build_frontend.log"
