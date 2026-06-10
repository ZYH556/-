"""Safety Gateway：输入闸门（规则优先，LLM 可选）+ 输出脱敏。

降级铁律：开关关 / 异常一律放行原文，绝不因安全检查阻断核心体验且无解释；
被拦截/脱敏时返回结构化原因供审计。
"""

from __future__ import annotations

import logging

from reflexlearn.common.config import Settings, get_settings
from reflexlearn.safety.rules import has_secret, redact_secrets, scan_input
from reflexlearn.safety.schemas import SafetyAction, SafetyDecision

logger = logging.getLogger(__name__)


class SafetyGateway:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def check_input(self, text: str) -> SafetyDecision:
        if not self._settings.enable_safety_gateway:
            return SafetyDecision()
        try:
            reasons = scan_input(text or "")
        except Exception as exc:  # noqa: BLE001 - 安全检查失败不阻断主链路
            logger.info("safety input scan degraded: %s", exc)
            return SafetyDecision()
        if reasons:
            return SafetyDecision(
                allowed=False,
                action=SafetyAction.BLOCK,
                reasons=reasons,
                audit_required=True,
                confidence=0.9,
            )
        return SafetyDecision()

    def check_output(self, text: str) -> SafetyDecision:
        original = text or ""
        if not self._settings.enable_safety_gateway:
            return SafetyDecision(redacted_text=original)
        try:
            if has_secret(original):
                return SafetyDecision(
                    allowed=True,
                    action=SafetyAction.REDACT,
                    reasons=["secret_in_output"],
                    redacted_text=redact_secrets(original),
                    audit_required=True,
                    confidence=0.9,
                )
        except Exception as exc:  # noqa: BLE001
            logger.info("safety output scan degraded: %s", exc)
        return SafetyDecision(redacted_text=original)
