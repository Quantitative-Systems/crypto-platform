"""STRATA — 24/7/365 Production Watchdog & Recovery Supervisor.

Guarantees platform survival across crashes, network drops, and broker anomalies:
- Startup reconciliation guard: verifies zero unmanaged or orphan broker positions before supervisor activation
- Process heartbeat and liveness watchdog
- State checkpoint integrity and restore validator
- Fail-closed safe mode transition if discrepancy detected
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class WatchdogStatus:
    healthy: bool = True
    last_heartbeat_time: float = field(default_factory=time.time)
    heartbeat_count: int = 0
    safe_mode_active: bool = False
    safe_mode_reason: Optional[str] = None
    startup_reconciled: bool = False
    discrepancy_count: int = 0


class RecoveryWatchdog:
    """
    24/7 System Watchdog & Startup Integrity Guardian.
    """

    def __init__(
        self,
        checkpoint_dir: str = "data/checkpoints",
        heartbeat_timeout_seconds: float = 30.0,
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.status = WatchdogStatus()

    def record_heartbeat(self) -> None:
        """Records a keep-alive pulse from the main execution loop."""
        self.status.last_heartbeat_time = time.time()
        self.status.heartbeat_count += 1
        if not self.status.safe_mode_active:
            self.status.healthy = True

    def check_liveness(self) -> Tuple[bool, Optional[str]]:
        """Checks if process has exceeded maximum allowed silence window."""
        elapsed = time.time() - self.status.last_heartbeat_time
        if elapsed > self.heartbeat_timeout_seconds:
            msg = f"Watchdog heartbeat expired: {elapsed:.1f}s > {self.heartbeat_timeout_seconds:.1f}s"
            self.trigger_safe_mode(msg)
            return False, msg
        return True, None

    def trigger_safe_mode(self, reason: str) -> None:
        """Locks the system into fail-closed safe mode."""
        self.status.healthy = False
        self.status.safe_mode_active = True
        self.status.safe_mode_reason = reason
        self.status.discrepancy_count += 1
        logger.critical(f"WATCHDOG ENTERED SAFE MODE: {reason}")

    def verify_startup_reconciliation(
        self,
        internal_positions: List[Dict[str, Any]],
        broker_positions: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifies startup consistency between internal tracked positions and broker positions.
        
        Strict rule: The platform must NEVER start into blind trading with orphan or unmanaged positions.
        """
        internal_symbols = {p.get("symbol", "").upper() for p in internal_positions if float(p.get("quantity", 0.0)) > 0}
        broker_active = [p for p in broker_positions if float(p.get("quantity", 0.0)) > 0]
        broker_symbols = {p.get("symbol", "").upper() for p in broker_active}

        # Check for orphan broker positions not in internal book
        orphan_positions = broker_symbols - internal_symbols
        if orphan_positions:
            reason = f"Startup reconciliation failed: detected orphan broker positions: {sorted(orphan_positions)}"
            self.trigger_safe_mode(reason)
            return False, reason

        # Check for ghost internal positions missing from broker
        ghost_positions = internal_symbols - broker_symbols
        if ghost_positions:
            reason = f"Startup reconciliation failed: detected ghost internal positions: {sorted(ghost_positions)}"
            self.trigger_safe_mode(reason)
            return False, reason

        self.status.startup_reconciled = True
        logger.info("Startup reconciliation verified: internal positions align with broker positions.")
        return True, None

    def save_checkpoint(self, state_dict: Dict[str, Any], filename: str = "system_checkpoint.json") -> Path:
        """Atomically saves and checksums a system checkpoint."""
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.checkpoint_dir / filename
        temp_path = self.checkpoint_dir / f"{filename}.tmp"

        payload = {
            "timestamp": time.time(),
            "state": state_dict,
        }
        raw_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        payload["sha256"] = hashlib.sha256(raw_bytes).hexdigest()

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        temp_path.replace(target_path)
        return target_path

    def load_and_verify_checkpoint(self, filename: str = "system_checkpoint.json") -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Loads and verifies checksum of system checkpoint."""
        target_path = self.checkpoint_dir / filename
        if not target_path.exists():
            return None, "Checkpoint file does not exist"

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            stored_hash = data.get("sha256")
            state = data.get("state")
            timestamp = data.get("timestamp")

            # Verify integrity
            verify_payload = {
                "timestamp": timestamp,
                "state": state,
            }
            computed_hash = hashlib.sha256(json.dumps(verify_payload, indent=2, sort_keys=True).encode("utf-8")).hexdigest()

            if stored_hash != computed_hash:
                err = f"Checkpoint corrupted: hash mismatch {stored_hash} != {computed_hash}"
                self.trigger_safe_mode(err)
                return None, err

            return state, None
        except Exception as e:
            err = f"Failed to load checkpoint: {e}"
            self.trigger_safe_mode(err)
            return None, err
