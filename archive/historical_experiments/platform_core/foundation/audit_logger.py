"""
Quantitative Crypto Platform (QCP) — Cryptographic Audit Logger.

Provides append-only structured audit logs with SHA-256 block chaining,
ensuring tamper-evident provenance across all platform decisions.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from enum import Enum
from platform_core.foundation.correlation import get_current_correlation_id, generate_event_id


class AuditLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditLogger:
    """
    Append-only cryptographically chained audit logger.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            base = Path(__file__).resolve().parent.parent.parent
            log_path = base / "research" / "results" / "telemetry" / "platform_audit_ledger.jsonl"
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = self._recover_last_hash()

    def _recover_last_hash(self) -> str:
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return self.GENESIS_HASH
        last_line = ""
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line
        if not last_line:
            return self.GENESIS_HASH
        try:
            record = json.loads(last_line)
            return record.get("current_hash", self.GENESIS_HASH)
        except Exception:
            return self.GENESIS_HASH

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        details: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cid = correlation_id or get_current_correlation_id()
        eid = generate_event_id("aud")
        now_iso = datetime.now(timezone.utc).isoformat()

        payload = {
            "entry_id": eid,
            "correlation_id": cid,
            "timestamp_utc": now_iso,
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "details": details,
            "previous_hash": self._last_hash,
        }

        # Calculate SHA-256 of canonical JSON payload
        canonical_str = json.dumps(payload, sort_keys=True)
        current_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
        payload["current_hash"] = current_hash

        # Append to disk
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

        self._last_hash = current_hash
        return payload

    def verify_ledger_integrity(self) -> bool:
        """Verifies the unbroken cryptographic hash chain from genesis to head."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return True

        expected_prev = self.GENESIS_HASH
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                if not line.strip():
                    continue
                record = json.loads(line)
                prev_hash = record.get("previous_hash")
                curr_hash = record.get("current_hash")
                if prev_hash != expected_prev:
                    return False

                # Recompute hash
                check_dict = {k: v for k, v in record.items() if k != "current_hash"}
                recomputed = hashlib.sha256(json.dumps(check_dict, sort_keys=True).encode("utf-8")).hexdigest()
                if recomputed != curr_hash:
                    return False
                expected_prev = curr_hash

        return True
