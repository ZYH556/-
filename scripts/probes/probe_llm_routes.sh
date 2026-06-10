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
  log_header "probe_llm_routes"
  "$(python_cmd)" - <<'PY'
import asyncio
from urllib.parse import urljoin

import httpx

from reflexlearn.common.config import get_settings


ROUTES = (
    "/v1/chat/completions",
    "/chat/completions",
    "/api/v1/chat/completions",
    "/api/openai/v1/chat/completions",
    "/openai/v1/chat/completions",
    "/v1/responses",
    "/responses",
    "/api/v1/responses",
)


def _join(base: str, route: str) -> str:
    return urljoin(base.rstrip("/") + "/", route.lstrip("/"))


async def _probe(client: httpx.AsyncClient, url: str, payload: dict, key: str) -> None:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    try:
        resp = await client.post(url, headers=headers, json=payload)
    except Exception as exc:
        print(f"{url} -> error:{type(exc).__name__}:{str(exc)[:160]}")
        return
    preview = resp.text.replace("\n", " ")[:220]
    print(f"{url} -> {resp.status_code} {preview}")


async def main() -> None:
    s = get_settings()
    if not (s.openai_compat_api_key and s.openai_compat_base_url and s.openai_compat_model):
        print("openai_compat=missing")
        raise SystemExit(1)
    print(f"base_url={s.openai_compat_base_url}")
    print(f"model={s.openai_compat_model}")
    print("api_key=SET")
    chat_payload = {
        "model": s.openai_compat_model,
        "messages": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_tokens": 8,
    }
    responses_payload = {
        "model": s.openai_compat_model,
        "input": [{"role": "user", "content": "ping"}],
        "temperature": 0,
        "max_output_tokens": 8,
    }
    async with httpx.AsyncClient(timeout=s.llm_request_timeout_s) as client:
        for route in ROUTES:
            payload = responses_payload if "responses" in route else chat_payload
            await _probe(client, _join(s.openai_compat_base_url, route), payload, s.openai_compat_api_key)


asyncio.run(main())
PY
} 2>&1 | tee -a "$LOG_DIR/probe_llm_routes.log"
