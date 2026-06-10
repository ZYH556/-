#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root

{
  log_header "check_frontend_ia"
  required=(
    "frontend/app/(public)/page.tsx"
    "frontend/app/(public)/tracks/[slug]/page.tsx"
    "frontend/app/(app)/layout.tsx"
    "frontend/app/(app)/spaces/page.tsx"
    "frontend/app/(app)/chat/page.tsx"
    "frontend/app/(app)/plan/page.tsx"
    "frontend/app/(app)/resources/page.tsx"
    "frontend/app/(app)/knowledge/page.tsx"
    "frontend/app/(app)/mistakes/page.tsx"
    "frontend/app/(app)/growth/page.tsx"
    "frontend/lib/nav.ts"
  )
  for path in "${required[@]}"; do
    [[ -f "$path" ]] || { echo "missing $path" >&2; exit 1; }
  done
  grep -q "/spaces" "frontend/app/(app)/spaces/page.tsx"
  grep -q "/resources" "frontend/app/(app)/resources/page.tsx"
  grep -q "/knowledge/documents" "frontend/app/(app)/knowledge/page.tsx"
  grep -q "/growth/lora-samples" "frontend/app/(app)/growth/page.tsx"
  grep -q "workspaceNavItems" "frontend/lib/nav.ts"
  echo "check_frontend_ia: ok"
} 2>&1 | tee -a "$LOG_DIR/check_frontend_ia.log"
