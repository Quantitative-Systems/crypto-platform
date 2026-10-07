"""Unit tests for STRATA Alert Router & Credential Sanitizer."""
import pytest
from notifications.alert_router import (
    ALERTS,
    AlertCategory,
    AlertSeverity,
    CredentialSanitizer,
)


def test_credential_sanitizer_redacts_secrets():
    dirty_text = "Connecting with api_key: 'abcdef1234567890' and secret: 'super_secret_value_123'"
    clean_text = CredentialSanitizer.sanitize(dirty_text)
    assert "abcdef1234567890" not in clean_text
    assert "super_secret_value_123" not in clean_text
    assert "[REDACTED_SECRET]" in clean_text


def test_alert_router_emit_and_retrieve():
    event = ALERTS.emit(
        severity=AlertSeverity.WARNING,
        category=AlertCategory.RISK,
        title="Test Heat Warning",
        message="Portfolio heat reached 2.8%",
        metadata={"heat_pct": 2.8, "secret_key": "private_secret_12345"},
    )
    assert event.alert_id.startswith("ALT_")
    assert event.severity == AlertSeverity.WARNING
    assert event.category == AlertCategory.RISK
    # Ensure metadata key was redacted
    assert event.metadata.get("secret_key") == "[REDACTED_SECRET]"

    recent = ALERTS.get_recent_alerts(limit=10)
    assert any(a["alert_id"] == event.alert_id for a in recent)
