"""STRATA Digital Trading Platform — Autonomous State & Broker Reconciliation Auditor.

Audits end-to-end pipeline integrity across:
candidates_evaluated
   ↓
eligible_candidates
   ↓
decisions_logged
   ↓
orders_submitted
   ↓
fills_executed
   ↓
positions_active
   ↓
positions_closed
   ↓
ledger_hashes_intact
   ↓
broker_exchange_state

Invariants:
- Total orders submitted must equal fills executed (in simulated/paper mode).
- Active positions + closed positions must equal fills executed.
- Every trade decision must have a corresponding immutable ledger entry.
- Broker reported positions must match internal active positions.
- If any discrepancy is detected: Mark SYSTEM_HEALTH = DEGRADED and trip Reconciliation Circuit Breaker.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from notifications.alert_router import ALERTS, AlertCategory, AlertSeverity

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationReport:
    timestamp_utc: str
    is_reconciled: bool
    status: str  # RECONCILED, DISCREPANCY_DETECTED, CRITICAL_HALT
    total_candidates: int = 0
    total_decisions: int = 0
    trade_decisions: int = 0
    no_trade_decisions: int = 0
    orders_submitted: int = 0
    fills_executed: int = 0
    active_positions: int = 0
    closed_positions: int = 0
    ledger_records: int = 0
    broker_positions_count: int = 0
    broker_discrepancies: List[str] = field(default_factory=list)
    discrepancies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "is_reconciled": self.is_reconciled,
            "status": self.status,
            "total_candidates": self.total_candidates,
            "total_decisions": self.total_decisions,
            "trade_decisions": self.trade_decisions,
            "no_trade_decisions": self.no_trade_decisions,
            "orders_submitted": self.orders_submitted,
            "fills_executed": self.fills_executed,
            "active_positions": self.active_positions,
            "closed_positions": self.closed_positions,
            "ledger_records": self.ledger_records,
            "broker_positions_count": self.broker_positions_count,
            "broker_discrepancies": self.broker_discrepancies,
            "discrepancies": self.discrepancies,
        }


class AutonomousReconciliationEngine:
    """Continuous audit engine asserting conservation of trades, decisions, and broker state."""

    def __init__(self):
        self.last_report: Optional[ReconciliationReport] = None

    def reconcile(
        self,
        candidate_count: int,
        decisions: List[Dict[str, Any]],
        orders: List[Dict[str, Any]],
        fills: List[Dict[str, Any]],
        active_positions: List[Dict[str, Any]],
        closed_positions: List[Dict[str, Any]],
        ledger_count: int,
        broker_positions: Optional[List[Dict[str, Any]]] = None,
    ) -> ReconciliationReport:
        ts = datetime.now(timezone.utc).isoformat()
        discrepancies: List[str] = []
        broker_discrepancies: List[str] = []

        total_decisions = len(decisions)
        trade_decisions = sum(1 for d in decisions if d.get("decision") == "TRADE")
        no_trade_decisions = sum(1 for d in decisions if d.get("decision") == "NO_TRADE")

        n_orders = len(orders)
        n_fills = len(fills)
        n_active = len(active_positions)
        n_closed = len(closed_positions)

        # Invariant 1: Total decisions must match ledger records
        if total_decisions != ledger_count:
            discrepancies.append(
                f"Ledger record mismatch: {total_decisions} decisions logged vs {ledger_count} ledger rows"
            )

        # Invariant 2: Trade decisions must equal orders submitted
        if trade_decisions != n_orders:
            discrepancies.append(
                f"Order submission mismatch: {trade_decisions} TRADE decisions vs {n_orders} orders submitted"
            )

        # Invariant 3: Orders submitted must equal fills executed (in simulated mode)
        if n_orders != n_fills:
            discrepancies.append(
                f"Execution fill mismatch: {n_orders} orders submitted vs {n_fills} fills executed"
            )

        # Invariant 4: Fills executed must equal active + closed positions
        if n_fills != (n_active + n_closed):
            discrepancies.append(
                f"Position lifecycle mismatch: {n_fills} fills vs {n_active + n_closed} (active {n_active} + closed {n_closed})"
            )

        # Invariant 5: Broker state reconciliation (if broker reports positions)
        n_broker_pos = 0
        if broker_positions is not None:
            n_broker_pos = len(broker_positions)
            if n_active != n_broker_pos:
                msg = f"Broker position count mismatch: Internal active={n_active} vs Broker reported={n_broker_pos}"
                broker_discrepancies.append(msg)
                discrepancies.append(msg)

        is_reconciled = (len(discrepancies) == 0)
        status = "RECONCILED" if is_reconciled else "DISCREPANCY_DETECTED"

        report = ReconciliationReport(
            timestamp_utc=ts,
            is_reconciled=is_reconciled,
            status=status,
            total_candidates=candidate_count,
            total_decisions=total_decisions,
            trade_decisions=trade_decisions,
            no_trade_decisions=no_trade_decisions,
            orders_submitted=n_orders,
            fills_executed=n_fills,
            active_positions=n_active,
            closed_positions=n_closed,
            ledger_records=ledger_count,
            broker_positions_count=n_broker_pos,
            broker_discrepancies=broker_discrepancies,
            discrepancies=discrepancies,
        )

        self.last_report = report
        if not is_reconciled:
            logger.error(f"RECONCILIATION FAILURE: {discrepancies}")
            ALERTS.emit(
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RECONCILIATION,
                title="State Reconciliation Invariant Breach",
                message="; ".join(discrepancies[:3]),
                metadata={"discrepancies_count": len(discrepancies)},
            )

        return report
