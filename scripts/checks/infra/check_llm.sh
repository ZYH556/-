#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

{
  log_header "check_llm"
  "$(python_cmd)" - <<'PY'
import asyncio

from pydantic import BaseModel

from reflexlearn.llm_gateway.gateway import LLMGateway


class ProbeResult(BaseModel):
    ok: bool
    reasoning: str


async def main() -> None:
    try:
        completion = await LLMGateway().complete(
            [
                {
                    "role": "system",
                    "content": "你只输出 JSON，不要输出 Markdown 或额外解释。",
                },
                {
                    "role": "user",
                    "content": '请输出 {"ok": true, "reasoning": "llm probe ok"}',
                },
            ],
            task_type="judgment",
            schema=ProbeResult,
            temperature=0.0,
        )
    except Exception as exc:
        print(f"llm_probe=fail:{type(exc).__name__}:{str(exc)[:360]}")
        raise SystemExit(1)
    text = completion.text.strip()
    print(f"model_used={completion.model_used}")
    print(f"latency_ms={completion.latency_ms}")
    print(f"input_tokens={completion.input_tokens}")
    print(f"output_tokens={completion.output_tokens}")
    print(f"text_preview={text[:1000]}")
    try:
        ProbeResult.model_validate_json(text)
        print("json_parse=ok")
    except Exception as exc:
        print(f"json_parse=fail:{type(exc).__name__}:{str(exc)[:240]}")


asyncio.run(main())
PY
} 2>&1 | tee -a "$LOG_DIR/check_llm.log"
