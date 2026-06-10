#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_lib.sh"
ensure_logs
exec "$SCRIPT_DIR/checks/api/check_api_integrations.sh" "$@"
