"""
Quantitative Crypto Platform (QCP) — SaaS & Billing Abstraction.

Manages plans, entitlements, quota limits, and billing ledger.
Trading decision logic and risk algorithms remain strictly decoupled from billing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
import uuid


class PlanTier(str, Enum):
    RESEARCH_COMMUNITY = "RESEARCH_COMMUNITY"
    PRO_QUANT = "PRO_QUANT"
    INSTITUTIONAL = "INSTITUTIONAL"


@dataclass
class Entitlements:
    max_strategies: int
    max_backtests_per_day: int
    max_paper_capital_usd: float
    realtime_websocket_allowed: bool
    options_analytics_allowed: bool
    custom_risk_policy_allowed: bool


TIER_ENTITLEMENTS: Dict[PlanTier, Entitlements] = {
    PlanTier.RESEARCH_COMMUNITY: Entitlements(
        max_strategies=3,
        max_backtests_per_day=50,
        max_paper_capital_usd=100_000.0,
        realtime_websocket_allowed=False,
        options_analytics_allowed=False,
        custom_risk_policy_allowed=False,
    ),
    PlanTier.PRO_QUANT: Entitlements(
        max_strategies=20,
        max_backtests_per_day=500,
        max_paper_capital_usd=1_000_000.0,
        realtime_websocket_allowed=True,
        options_analytics_allowed=True,
        custom_risk_policy_allowed=False,
    ),
    PlanTier.INSTITUTIONAL: Entitlements(
        max_strategies=1000,
        max_backtests_per_day=50000,
        max_paper_capital_usd=100_000_000.0,
        realtime_websocket_allowed=True,
        options_analytics_allowed=True,
        custom_risk_policy_allowed=True,
    ),
}


@dataclass
class Invoice:
    invoice_id: str
    org_id: str
    amount_usd: float
    status: str  # PAID, PENDING, OVERDUE
    period_start: str
    period_end: str
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SaaSBillingEngine:
    """
    Manages tenant subscriptions and entitlement meters without touching trading code.
    """

    def __init__(self):
        self._subscriptions: Dict[str, PlanTier] = {}
        self._usage_backtests: Dict[str, int] = {}
        self._invoices: List[Invoice] = []

    def set_organization_tier(self, org_id: str, tier: PlanTier) -> None:
        self._subscriptions[org_id] = tier

    def get_entitlements(self, org_id: str) -> Entitlements:
        tier = self._subscriptions.get(org_id, PlanTier.INSTITUTIONAL)
        return TIER_ENTITLEMENTS[tier]

    def record_backtest_usage(self, org_id: str) -> bool:
        ent = self.get_entitlements(org_id)
        current = self._usage_backtests.get(org_id, 0)
        if current >= ent.max_backtests_per_day:
            return False
        self._usage_backtests[org_id] = current + 1
        return True

    def generate_monthly_invoice(self, org_id: str, amount_usd: float) -> Invoice:
        inv = Invoice(
            invoice_id=f"inv_{uuid.uuid4().hex[:12]}",
            org_id=org_id,
            amount_usd=amount_usd,
            status="PAID",
            period_start=datetime.now(timezone.utc).isoformat(),
            period_end=datetime.now(timezone.utc).isoformat(),
        )
        self._invoices.append(inv)
        return inv
