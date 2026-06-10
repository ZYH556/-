#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root

fail() {
  echo "check_frontend_glass: $1" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing file: $path"
}

require_text() {
  local path="$1"
  local text="$2"
  grep -Fq -- "$text" "$path" || fail "missing '$text' in $path"
}

{
  log_header "check_frontend_glass"

  require_file "frontend/app/globals.css"
  require_file "frontend/app/design/page.tsx"
  require_file "frontend/components/glass/index.ts"

  for component in GlassPanel GlassCard GlassButton GlassSidebar GlassModal; do
    require_file "frontend/components/glass/${component}.tsx"
    require_text "frontend/components/glass/index.ts" "$component"
  done

  require_text "frontend/app/globals.css" "@theme"
  require_text "frontend/app/globals.css" "--color-glass-surface"
  require_text "frontend/app/globals.css" ".glass"
  require_text "frontend/app/globals.css" ".glass-strong"
  require_text "frontend/app/globals.css" "prefers-reduced-motion"
  require_text "frontend/app/globals.css" "@supports not"

  for dir in chat resource tools glass cards; do
    [[ -d "frontend/components/$dir" ]] || fail "missing directory: frontend/components/$dir"
  done

  root_entries="$(find frontend/components -mindepth 1 -maxdepth 1 | wc -l | tr -d ' ')"
  [[ "$root_entries" -le 8 ]] || fail "frontend/components root has $root_entries entries"

  while IFS= read -r file; do
    lines="$(wc -l < "$file" | tr -d ' ')"
    [[ "$lines" -le 300 ]] || fail "$file has $lines lines"
  done < <(find frontend/app frontend/components -type f \( -name '*.tsx' -o -name '*.css' \))

  echo "check_frontend_glass: ok"
} 2>&1 | tee -a "$LOG_DIR/check_frontend_glass.log"
