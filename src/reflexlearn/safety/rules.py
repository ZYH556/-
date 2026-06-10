"""规则引擎：prompt injection / 索要系统提示 / 恶意代码 / 跨租户越权 / 密钥泄漏。

规则优先、确定性、无外部依赖；LLM safety checker 作为可选增强（默认关）。
注意：输入闸门只拦明显恶意/注入/越权；用户输入中出现疑似密钥不直接拦截
（可能是正常讨论），密钥治理交给输出脱敏。
"""

from __future__ import annotations

import re

# —— 索要系统提示 / prompt injection ——
_PROMPT_INJECTION = [
    re.compile(
        r"(忽略|无视|ignore|disregard).{0,16}(之前|上述|previous|above|all|先前).{0,16}"
        r"(指令|说明|instruction|prompt|规则)",
        re.I,
    ),
    re.compile(r"(系统提示词?|system\s*prompt|你的提示词|developer\s*message|开发者消息)", re.I),
    re.compile(
        r"(reveal|show|print|输出|打印|告诉我|repeat).{0,20}(system\s*prompt|系统提示|"
        r"your\s*instructions|你的指令)",
        re.I,
    ),
]

# —— 恶意代码 / 危险请求 ——
_MALICIOUS = [
    re.compile(r"(rm\s+-rf\s+/|format\s+c:|del\s+/[sfq])", re.I),
    re.compile(
        r"(写|生成|帮我做|帮我写|create|write|build).{0,24}"
        r"(勒索软件|病毒|木马|蠕虫|ransomware|malware|keylogger|后门|backdoor|rootkit)",
        re.I,
    ),
    re.compile(r"(发起|实施|launch|perform).{0,16}(ddos|sql\s*注入攻击|拖库|脱裤|撞库)", re.I),
]

# —— 跨租户 / 越权提权 ——
_CROSS_TENANT = [
    re.compile(
        r"(其他|别的|所有|other|all)\s*(用户|租户|学员|user|tenant|account).{0,16}"
        r"(数据|资料|密码|私信|隐私|data|password|secret)",
        re.I,
    ),
    re.compile(
        r"(绕过|bypass|越权|提权|privilege\s*escalation).{0,16}"
        r"(权限|认证|鉴权|auth|permission|acl|登录)",
        re.I,
    ),
]

# —— 密钥 / token 泄漏样式（用于输出脱敏）——
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    re.compile(
        r"(api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd)\s*[:=]\s*"
        r"['\"]?[A-Za-z0-9._\-]{8,}",
        re.I,
    ),
]


def scan_input(text: str) -> list[str]:
    """返回命中的高危类别（空列表表示放行）。"""
    reasons: list[str] = []
    if any(p.search(text) for p in _PROMPT_INJECTION):
        reasons.append("prompt_injection")
    if any(p.search(text) for p in _MALICIOUS):
        reasons.append("malicious_request")
    if any(p.search(text) for p in _CROSS_TENANT):
        reasons.append("cross_tenant_or_privilege")
    return reasons


def has_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


def redact_secrets(text: str) -> str:
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    return out
