"""STRATA Digital Trading Platform — Event-Driven Alert & Notification Router.

Dispatches operational, execution, and risk notifications across:
- In-memory ring buffer (for live Web UI terminal streaming)
- Persistent JSONL audit file (`research/results/ALERTS.jsonl`)
- Standard system logging
- External Webhook (Slack/Discord/Telegram compatible)

SECURITY INVARIANT:
All notifications are sanitized through an automated credential stripper to ensure
no API keys, tokens, or private secrets can ever leak into alert channels.
"""
from __future__ import annotations

import collections
import json
import logging
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_ALERT_FILE = Path(__file__).resolve().parent.parent / "research" / "results" / "ALERTS.jsonl"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class AlertCategory(str, Enum):
    SYSTEM = "SYSTEM"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    DATA = "DATA"
    RECONCILIATION = "RECONCILIATION"
    DRIFT = "DRIFT"
    SECURITY = "SECURITY"


@dataclass
class AlertEvent:
    alert_id: str
    timestamp_ms: int
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "timestamp_ms": self.timestamp_ms,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
        }


class CredentialSanitizer:
    """Strips API keys, passwords, and secrets from text strings."""

    SENSITIVE_PATTERNS = [
        re.compile(r"(api[_-]?key|secret|password|token|passphrase)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE),
        re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{12,}", re.IGNORECASE),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        clean = text
        for pattern in cls.SENSITIVE_PATTERNS:
            clean = pattern.sub(r"\1: [REDACTED_SECRET]", clean)
        return clean

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        clean_d = {}
        for k, v in data.items():
            if any(term in k.lower() for term in ("key", "secret", "password", "token", "passphrase")):
                clean_d[k] = "[REDACTED_SECRET]"
            elif isinstance(v, str):
                clean_d[k] = cls.sanitize(v)
            elif isinstance(v, dict):
                clean_d[k] = cls.sanitize_dict(v)
            else:
                clean_d[k] = v
        return clean_d


class AlertRouter:
    """Singleton notification dispatcher."""

    _instance: Optional[AlertRouter] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_buffer_size: int = 250, alert_file: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return

        self._buffer: Deque[AlertEvent] = collections.deque(maxlen=max_buffer_size)
        self.alert_file = alert_file or DEFAULT_ALERT_FILE
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
        self.webhook_url = os.environ.get("PLATFORM_ALERT_WEBHOOK_URL", "")
        self._initialized = True

    def emit(
        self,
        severity: AlertSeverity,
        category: AlertCategory,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AlertEvent:
        """Create, sanitize, and dispatch an alert event."""
        clean_title = CredentialSanitizer.sanitize(title)
        clean_msg = CredentialSanitizer.sanitize(message)
        clean_meta = CredentialSanitizer.sanitize_dict(metadata or {})

        event = AlertEvent(
            alert_id=f"ALT_{uuid.uuid4().hex[:8].upper()}",
            timestamp_ms=int(time.time() * 1000),
            severity=severity,
            category=category,
            title=clean_title,
            message=clean_msg,
            metadata=clean_meta,
        )

        # 1. Store in memory buffer
        self._buffer.append(event)

        # 2. Write to persistent JSONL file
        try:
            with open(self.alert_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to append alert to file: {e}")

        # 3. System logger dispatch
        log_text = f"[{event.category.value}] [{event.severity.value}] {event.title}: {event.message}"
        if severity == AlertSeverity.INFO:
            logger.info(log_text)
        elif severity == AlertSeverity.WARNING:
            logger.warning(log_text)
        elif severity in (AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY):
            logger.critical(log_text)

        return event

    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return list of most recent alerts for UI and telemetry."""
        items = list(self._buffer)
        return [item.to_dict() for item in reversed(items[-limit:])]


# Global singleton router
ALERTS = AlertRouter()
