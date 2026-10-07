"""Crypto Trading Platform — Continuous State Reconciliation Engine.

Runs continuously to audit local internal state against exchange reality:
- Compares internal open orders vs venue open orders.
- Compares internal positions vs venue positions.
- Freezes trading via RiskFirewall on any unexplained discrepancy.
- Restores internal state from exchange truth without creating duplicate orders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import ExecutionOrder, OrderStatus, Position
from crypto_platform.core.interfaces import (
    IExchangeAdapter,
    IOrderManagementSystem,
    IReconciliationEngine,
)

logger = logging.getLogger("crypto_platform.reconciliation")


@dataclass
class ReconciliationReport:
    account_id: str
    venue: str
    timestamp_ms: int
    is_in_sync: bool
    discrepancies: List[str] = field(default_factory=list)
    resolved: bool = False


class StateReconciliationEngine(IReconciliationEngine):
    """Audits and synchronizes local OMS state against external exchange state."""

    def __init__(self, tolerance_usd: float = 0.01, risk_firewall: Optional[Any] = None):
        self.tolerance_usd = tolerance_usd
        self.risk_firewall = risk_firewall
        self.reports_history: List[ReconciliationReport] = []

    async def reconcile_account(
        self, account_id: str, adapter: IExchangeAdapter, oms: IOrderManagementSystem
    ) -> bool:
        """Execute full reconciliation pass for an account."""
        now_ms = int(time.time() * 1000)
        discrepancies: List[str] = []

        try:
            # 1. Fetch exchange reality
            remote_positions = await adapter.get_positions()
            remote_orders = await adapter.get_open_orders()

            # 2. Fetch local internal state
            local_positions = oms.get_positions(account_id)
            local_orders = oms.get_open_orders(account_id)

            # Compare Positions
            remote_pos_map = {p.symbol: p for p in remote_positions if p.size > 0}
            all_symbols = set(local_positions.keys()).union(set(remote_pos_map.keys()))

            for sym in all_symbols:
                loc = local_positions.get(sym)
                rem = remote_pos_map.get(sym)

                loc_size = loc.size * loc.direction if loc else 0.0
                rem_size = rem.size * rem.direction if rem else 0.0

                if abs(loc_size - rem_size) > 1e-6:
                    discrepancies.append(
                        f"Position mismatch on {sym}: local={loc_size}, exchange={rem_size}"
                    )

            # Compare Open Orders
            remote_cid_set = {o.client_order_id for o in remote_orders}
            local_cid_set = {o.client_order_id for o in local_orders}

            missing_on_exchange = local_cid_set - remote_cid_set
            if missing_on_exchange:
                discrepancies.append(
                    f"Ghost orders (exist locally, missing on exchange): {missing_on_exchange}"
                )

            unexpected_on_exchange = remote_cid_set - local_cid_set
            if unexpected_on_exchange:
                discrepancies.append(
                    f"Untracked orders on exchange: {unexpected_on_exchange}"
                )

        except Exception as e:
            discrepancies.append(f"Reconciliation query error: {str(e)}")

        is_in_sync = len(discrepancies) == 0

        # Update Risk Firewall to freeze new orders if out of sync
        if self.risk_firewall:
            self.risk_firewall.set_reconciliation_status(account_id, is_in_sync)
            has_ghost_orders = any("Ghost" in d for d in discrepancies)
            if has_ghost_orders:
                self.risk_firewall.set_unknown_order_state(account_id, True)

        report = ReconciliationReport(
            account_id=account_id,
            venue=adapter.venue_name,
            timestamp_ms=now_ms,
            is_in_sync=is_in_sync,
            discrepancies=discrepancies,
        )
        self.reports_history.append(report)
        return is_in_sync

    async def restore_state_from_exchange(
        self, account_id: str, adapter: IExchangeAdapter, oms: IOrderManagementSystem
    ) -> bool:
        """Restores local state from exchange ground truth without placing new orders."""
        try:
            remote_positions = await adapter.get_positions()
            remote_orders = await adapter.get_open_orders()

            # 1. Synchronize positions in OMS
            acct_pos = getattr(oms, "_positions", {}).setdefault(account_id, {})
            acct_pos.clear()
            for p in remote_positions:
                if p.size > 0:
                    acct_pos[p.symbol] = p

            # 2. Synchronize open orders in OMS
            local_orders = oms.get_open_orders(account_id)
            remote_cid_map = {o.client_order_id: o for o in remote_orders}

            for loc in local_orders:
                if loc.client_order_id not in remote_cid_map:
                    # Cancel locally or set to UNKNOWN -> CANCELLED
                    oms.update_order_status(
                        account_id,
                        loc.order_id,
                        OrderStatus.CANCELLED,
                        message="Reconciliation: order absent on exchange",
                    )

            for rem in remote_orders:
                acct_orders = getattr(oms, "_orders", {}).setdefault(account_id, {})
                if rem.order_id not in acct_orders:
                    acct_orders[rem.order_id] = rem
                    getattr(oms, "_cid_map", {}).setdefault(account_id, {})[rem.client_order_id] = rem.order_id

            # 3. Clear Risk Firewall locks once restored
            if self.risk_firewall:
                self.risk_firewall.set_reconciliation_status(account_id, True)
                self.risk_firewall.set_unknown_order_state(account_id, False)

            logger.info(f"Account {account_id} state successfully restored from exchange.")
            return True

        except Exception as e:
            logger.error(f"Failed to restore state from exchange for {account_id}: {e}")
            return False
