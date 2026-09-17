"""
Production Reconciliation - EOD Reconciler.

End-of-day ledger reconciliation engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import time


@dataclass(frozen=True)
class ReconciliationReport:
    timestamp_utc: int
    internal_nav: float
    exchange_balance: float
    discrepancy_usd: float
    is_clean: bool
    position_mismatches: List[str]
    notes: Optional[str] = None


class EODReconciler:
    @staticmethod
    def audit(
        internal_nav: float,
        exchange_balance: float,
        active_positions: Dict[str, Dict[str, Any]],
        exchange_positions: Dict[str, Dict[str, Any]],
        max_tolerable_discrepancy_usd: float = 1.00,
    ) -> ReconciliationReport:
        now_ts = int(time.time())
        diff = abs(internal_nav - exchange_balance)
        mismatches: List[str] = []
        for sym, internal_pos in active_positions.items():
            if sym not in exchange_positions:
                mismatches.append(f"Position {sym} active internally but missing on exchange.")
            else:
                ex_pos = exchange_positions[sym]
                ex_qty = ex_pos.get("quantity", ex_pos.get("units", 0))
                int_qty = internal_pos.get("quantity", internal_pos.get("units", 0))
                if abs(ex_qty - int_qty) > 1e-4:
                    mismatches.append(f"Size mismatch on {sym}: internal={int_qty} vs exchange={ex_qty}")
        is_clean = (diff <= max_tolerable_discrepancy_usd) and (len(mismatches) == 0)
        notes = "Reconciliation Passed" if is_clean else f"Discrepancy detected: ${diff:.2f}"
        return ReconciliationReport(
            timestamp_utc=now_ts, internal_nav=internal_nav, exchange_balance=exchange_balance,
            discrepancy_usd=diff, is_clean=is_clean, position_mismatches=mismatches, notes=notes,
        )

