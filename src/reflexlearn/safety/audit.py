"""Safety 审计：复用 security.audit 的事件模型，统一安全事件落库/日志。"""

from __future__ import annotations

from reflexlearn.safety.schemas import SafetyAction, SafetyDecision
from reflexlearn.security.audit import AuditEvent


def safety_audit_event(
    *,
    stage: str,
    decision: SafetyDecision,
    user_id: str = "",
    tenant_id: str = "",
    ip: str = "",
) -> AuditEvent:
    if not decision.allowed:
        status = "blocked"
    elif decision.action == SafetyAction.REDACT:
        status = "redacted"
    else:
        status = "ok"
    return AuditEvent(
        event_type=f"safety.{stage}",
        user_id=user_id,
        tenant_id=tenant_id,
        ip=ip,
        status=status,
        detail={"reasons": decision.reasons, "confidence": decision.confidence},
    )
