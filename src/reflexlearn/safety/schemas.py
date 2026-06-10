"""Safety Gateway 强类型决策。"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SafetyAction(str, Enum):
    ALLOW = "allow"
    REDACT = "redact"
    BLOCK = "block"


class SafetyDecision(BaseModel):
    allowed: bool = True
    action: SafetyAction = SafetyAction.ALLOW
    reasons: list[str] = Field(default_factory=list)
    redacted_text: str = ""
    audit_required: bool = False
    confidence: float = 1.0
