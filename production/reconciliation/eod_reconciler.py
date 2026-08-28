"""
Product 07 — Production Service & Reliability
EOD Ledger Reconciliation Engine.
Audits live exchange balances and fills against internal portfolio accounting.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from portfolio_engine.contracts.portfolio_state import PortfolioState
from execution_gateway.interfaces.base_gateway import BaseGateway


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
    """
    Performs daily reconciliation audits comparing internal state with exchange reality.
    """

    @staticmethod
    async def audit(
        portfolio_state: PortfolioState,
        gateway: BaseGateway,
        max_tolerable_discrepancy_usd: float = 1.00
    ) -> ReconciliationReport:
        import time
        now_ts = int(time.time())

        # 1. Fetch Exchange Balance
        exchange_bal = await gateway.get_account_balance()
        internal_nav = portfolio_state.nav
        diff = abs(internal_nav - exchange_bal)

        # 2. Fetch Exchange Positions
        exchange_positions = await gateway.get_positions()
        mismatches: List[str] = []

        # Check internal vs exchange
        for sym, internal_pos in portfolio_state.active_positions.items():
            if sym not in exchange_positions:
                mismatches.append(f"Position {sym} active internally but missing on exchange.")
            else:
                ex_pos = exchange_positions[sym]
                if abs(ex_pos.quantity - internal_pos["units"]) > 1e-4:
                    mismatches.append(
                        f"Size mismatch on {sym}: internal={internal_pos['units']} vs exchange={ex_pos.quantity}"
                    )

        is_clean = (diff <= max_tolerable_discrepancy_usd) and (len(mismatches) == 0)
        notes = "Reconciliation Passed" if is_clean else f"Discrepancy detected: ${diff:.2f}"

        return ReconciliationReport(
            timestamp_utc=now_ts,
            internal_nav=internal_nav,
            exchange_balance=exchange_bal,
            discrepancy_usd=diff,
            is_clean=is_clean,
            position_mismatches=mismatches,
            notes=notes
        )
