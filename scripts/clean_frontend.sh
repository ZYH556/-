#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"

ensure_logs
cd_root

{
  log_header "clean_frontend"
  if command -v powershell.exe >/dev/null 2>&1; then
    if command -v wslpath >/dev/null 2>&1; then
      PS_PROJECT_ROOT="$(wslpath -w "$PROJECT_ROOT")"
    elif command -v cygpath >/dev/null 2>&1; then
      PS_PROJECT_ROOT="$(cygpath -w "$PROJECT_ROOT")"
    else
      PS_PROJECT_ROOT="$PROJECT_ROOT"
    fi
    powershell.exe -NoProfile -Command "\
      \$root = (Resolve-Path '$PS_PROJECT_ROOT').Path; \
      \$target = Join-Path \$root 'frontend\\.next'; \
      if (-not (Test-Path -LiteralPath \$target)) { Write-Output \"No frontend .next cache found\"; exit 0 } \
      \$resolved = (Resolve-Path -LiteralPath \$target).Path; \
      if (-not \$resolved.StartsWith((Join-Path \$root 'frontend'), [System.StringComparison]::OrdinalIgnoreCase)) { throw \"Refusing to remove unexpected path: \$resolved\" } \
      Write-Output \"Removing \$resolved\"; \
      Remove-Item -LiteralPath \$resolved -Recurse -Force"
  else
    target="$PROJECT_ROOT/frontend/.next"
    case "$(cd "$(dirname "$target")" && pwd)/$(basename "$target")" in
      "$PROJECT_ROOT/frontend/.next")
        rm -rf "$target"
        ;;
      *)
        echo "Refusing to remove unexpected path: $target" >&2
        exit 1
        ;;
    esac
  fi
} 2>&1 | tee -a "$LOG_DIR/clean_frontend.log"
