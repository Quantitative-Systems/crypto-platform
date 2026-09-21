"""
Quantitative Crypto Platform (QCP) — Disaster Recovery & Chaos Orchestrator.

Implements automated state snapshotting, position reconciliation, and chaos
failure injection (network drops, exchange halts, corrupted bars, process kills).
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class DisasterRecoverySnapshot:
    snapshot_id: str
    timestamp_utc: str
    equity_usd: float
    active_positions: List[Dict[str, Any]]
    open_orders: List[Dict[str, Any]]
    risk_state: Dict[str, Any]
    checksum: str


class DisasterRecoveryOrchestrator:
    """
    Manages crash resilience, backup creation, state reconstruction, and chaos drills.
    """

    def __init__(self, backup_dir: Optional[Path] = None):
        base = Path(__file__).resolve().parent.parent
        self.backup_dir = backup_dir or base / "research" / "results" / "dr_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._chaos_faults_active: Dict[str, bool] = {}

    def create_state_snapshot(
        self,
        equity_usd: float,
        active_positions: List[Dict[str, Any]],
        open_orders: List[Dict[str, Any]],
        risk_state: Dict[str, Any],
    ) -> Path:
        import hashlib
        now_iso = datetime.now(timezone.utc).isoformat()
        sid = f"snap_{int(datetime.now(timezone.utc).timestamp())}"

        state = {
            "snapshot_id": sid,
            "timestamp_utc": now_iso,
            "equity_usd": equity_usd,
            "active_positions": active_positions,
            "open_orders": open_orders,
            "risk_state": risk_state,
        }
        checksum = hashlib.sha256(json.dumps(state, sort_keys=True).encode("utf-8")).hexdigest()
        state["checksum"] = checksum

        snap_file = self.backup_dir / f"{sid}.json"
        with open(snap_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        return snap_file

    def restore_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        import hashlib
        files = sorted(self.backup_dir.glob("snap_*.json"))
        if not files:
            return None
        latest = files[-1]
        with open(latest, "r", encoding="utf-8") as f:
            state = json.load(f)

        stored_cs = state.get("checksum")
        check_dict = {k: v for k, v in state.items() if k != "checksum"}
        calc_cs = hashlib.sha256(json.dumps(check_dict, sort_keys=True).encode("utf-8")).hexdigest()
        if stored_cs != calc_cs:
            raise RuntimeError(f"FATAL: Backup snapshot {latest.name} corrupted. Checksum mismatch.")

        return state

    def inject_fault(self, fault_type: str) -> None:
        """Supported: 'NETWORK_DROP', 'EXCHANGE_500', 'CORRUPT_BAR', 'STALE_TICK'"""
        self._chaos_faults_active[fault_type] = True

    def clear_fault(self, fault_type: str) -> None:
        self._chaos_faults_active.pop(fault_type, None)

    def is_fault_active(self, fault_type: str) -> bool:
        return self._chaos_faults_active.get(fault_type, False)
