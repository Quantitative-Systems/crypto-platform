"""
Quantitative Crypto Platform (QCP) — Unified Event & Correlation Identifiers.

Propagates correlation_id, event_id, causation_id across microservice boundaries
and asynchronous event pipelines.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_CORRELATION_ID_CTX: ContextVar[str] = ContextVar("correlation_id", default="")
_CAUSATION_ID_CTX: ContextVar[str] = ContextVar("causation_id", default="")


def generate_event_id(prefix: str = "evt") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def get_current_correlation_id() -> str:
    cid = _CORRELATION_ID_CTX.get()
    if not cid:
        cid = generate_event_id("corr")
        _CORRELATION_ID_CTX.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    _CORRELATION_ID_CTX.set(correlation_id)


def get_current_causation_id() -> str:
    return _CAUSATION_ID_CTX.get()


def set_causation_id(causation_id: str) -> None:
    _CAUSATION_ID_CTX.set(causation_id)


@dataclass(frozen=True)
class EventMetadata:
    event_id: str = field(default_factory=lambda: generate_event_id("evt"))
    correlation_id: str = field(default_factory=get_current_correlation_id)
    causation_id: str = field(default_factory=get_current_causation_id)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_service: str = "qcp_platform"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "timestamp_utc": self.timestamp_utc,
            "source_service": self.source_service,
        }


class CorrelationContext:
    """Context manager for correlation scoping."""

    def __init__(self, correlation_id: Optional[str] = None, causation_id: Optional[str] = None):
        self.correlation_id = correlation_id or generate_event_id("corr")
        self.causation_id = causation_id or ""
        self._tokens = []

    def __enter__(self) -> CorrelationContext:
        self._tokens.append(_CORRELATION_ID_CTX.set(self.correlation_id))
        if self.causation_id:
            self._tokens.append(_CAUSATION_ID_CTX.set(self.causation_id))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for token in reversed(self._tokens):
            if token.var == _CORRELATION_ID_CTX:
                _CORRELATION_ID_CTX.reset(token)
            elif token.var == _CAUSATION_ID_CTX:
                _CAUSATION_ID_CTX.reset(token)
