#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPTS_ROOT/_lib.sh"

ensure_logs
cd_root
use_local_network
use_python_defaults

# /api/chat 真实 SSE 性能采集：TTFC（首个 resource_card）+ 总时长（done）+ 网关 LLM 调用数。
# 度量是 PERF 优化的验收前提（docs/19 §3）；分离「网关 LLM 调用」与「端到端」以隔离中转站变量。
PERF_PORT="${1:-8000}"

{
  log_header "check_chat_perf"
  PERF_PORT="$PERF_PORT" "$(python_cmd)" - <<'PY'
import os
import time

import httpx

port = os.environ.get("PERF_PORT", "8000")
base = f"http://127.0.0.1:{port}"
user = os.environ.get("REFLEXLEARN_HEALTH_USER", "admin")
pw = os.environ.get("REFLEXLEARN_HEALTH_PASSWORD", "reflexlearn-admin")


def llm_total() -> float | None:
    try:
        with httpx.Client(trust_env=False, timeout=10) as c:
            txt = c.get(f"{base}/metrics").text
        total = 0.0
        for line in txt.splitlines():
            if line.startswith("reflexlearn_llm_requests_total") and " " in line:
                total += float(line.rsplit(" ", 1)[-1])
        return total
    except Exception:
        return None


with httpx.Client(trust_env=False, timeout=30) as c:
    r = c.post(f"{base}/api/auth/login", json={"username": user, "password": pw})
    if r.status_code != 200:
        raise SystemExit(f"[FAIL] login status {r.status_code}")
    token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"} if token else {}

llm_before = llm_total()
body = {"message": "线性回归从入门到精通", "user_id": user}
t0 = time.time()
firsts: dict[str, float] = {}
frames: dict[str, int] = {}

with httpx.Client(trust_env=False, timeout=240) as c:
    with c.stream("POST", f"{base}/api/chat", json=body, headers=headers) as resp:
        if resp.status_code != 200:
            raise SystemExit(f"[FAIL] chat status {resp.status_code}")
        for line in resp.iter_lines():
            if not line or not line.startswith("event:"):
                continue
            ev = line[6:].strip()
            frames[ev] = frames.get(ev, 0) + 1
            firsts.setdefault(ev, round(time.time() - t0, 2))
            if ev == "done":
                break

llm_after = llm_total()
llm_calls = None if llm_before is None or llm_after is None else int(llm_after - llm_before)

signal = firsts.get("agent_step") or firsts.get("session")
ttfc = firsts.get("resource_card")
total = firsts.get("done")

print(f"[chat-perf] first_signal={signal}s  TTFC(resource_card)={ttfc}s  total(done)={total}s")
print(f"[chat-perf] llm_calls_this_request={llm_calls}  frames={frames}")

if total is None:
    raise SystemExit("[FAIL] no done frame (chat did not complete)")
print("[OK] chat perf captured")
PY
} 2>&1 | tee -a "$LOG_DIR/check_chat_perf.log"
