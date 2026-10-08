"""STRATA — Commercial Billing & Entitlements Engine.

Manages commercial tiers, plan entitlements, fee structures, and promotional launch policies.
During the initial public launch period:
- ALL USER CHARGES = $0.00 (First-Year Free Launch Period)
- Real capital execution remains fail-closed ($0.00).
- Transparent future fee schedules are recorded for disclosure without charging users.
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PlanTier(str, Enum):
    RESEARCHER = "RESEARCHER"
    TRADER = "TRADER"
    AUTONOMOUS = "AUTONOMOUS"
    INSTITUTIONAL = "INSTITUTIONAL"


@dataclass
class PlanDefinition:
    plan_id: str
    name: str
    tier: PlanTier
    launch_price_usd: float  # $0.00 during free launch period
    standard_price_usd: float  # Future scheduled transparent price
    billing_interval: str  # MONTHLY / ANNUAL
    max_broker_accounts: int
    max_active_strategies: int
    strategy_lab_access: bool
    ai_copilot_queries_per_day: int
    tick_level_history_access: bool
    sla_support_tier: str
    features: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "tier": self.tier.value,
            "launch_price_usd": self.launch_price_usd,
            "standard_price_usd": self.standard_price_usd,
            "billing_interval": self.billing_interval,
            "max_broker_accounts": self.max_broker_accounts,
            "max_active_strategies": self.max_active_strategies,
            "strategy_lab_access": self.strategy_lab_access,
            "ai_copilot_queries_per_day": self.ai_copilot_queries_per_day,
            "tick_level_history_access": self.tick_level_history_access,
            "sla_support_tier": self.sla_support_tier,
            "features": self.features,
        }


CANONICAL_PLANS: Dict[str, PlanDefinition] = {
    "RESEARCHER": PlanDefinition(
        plan_id="plan_researcher",
        name="Researcher",
        tier=PlanTier.RESEARCHER,
        launch_price_usd=0.00,
        standard_price_usd=0.00,
        billing_interval="MONTHLY",
        max_broker_accounts=1,
        max_active_strategies=3,
        strategy_lab_access=True,
        ai_copilot_queries_per_day=50,
        tick_level_history_access=False,
        sla_support_tier="COMMUNITY",
        features=[
            "Access to KING Core 7-timeframe fractal visualizer",
            "Natural language Strategy Lab (up to 3 concurrent models)",
            "Zero-capital paper simulation engine",
            "Community research discussions",
        ],
    ),
    "TRADER": PlanDefinition(
        plan_id="plan_trader",
        name="Trader",
        tier=PlanTier.TRADER,
        launch_price_usd=0.00,
        standard_price_usd=149.00,
        billing_interval="MONTHLY",
        max_broker_accounts=3,
        max_active_strategies=10,
        strategy_lab_access=True,
        ai_copilot_queries_per_day=250,
        tick_level_history_access=True,
        sla_support_tier="STANDARD",
        features=[
            "Everything in Researcher",
            "Multi-broker connectivity (Binance Testnet, Bybit Testnet, MT5 Demo)",
            "Automated order lifecycle audit trail (22 fields per trade)",
            "Real-time statistical drift and regime shift detection",
            "Standard email & webhook alerts",
        ],
    ),
    "AUTONOMOUS": PlanDefinition(
        plan_id="plan_autonomous",
        name="Autonomous Pro",
        tier=PlanTier.AUTONOMOUS,
        launch_price_usd=0.00,
        standard_price_usd=499.00,
        billing_interval="MONTHLY",
        max_broker_accounts=10,
        max_active_strategies=50,
        strategy_lab_access=True,
        ai_copilot_queries_per_day=1000,
        tick_level_history_access=True,
        sla_support_tier="PRIORITY",
        features=[
            "Everything in Trader",
            "Full Autonomous Trading Agent with real-time style switching",
            "24/7 Process Watchdog & continuous state reconciliation",
            "Cross-set coherence validation across all 5 timeframe sets",
            "Priority API rate limits and low-latency websocket channels",
        ],
    ),
    "INSTITUTIONAL": PlanDefinition(
        plan_id="plan_institutional",
        name="Institutional",
        tier=PlanTier.INSTITUTIONAL,
        launch_price_usd=0.00,
        standard_price_usd=1499.00,
        billing_interval="MONTHLY",
        max_broker_accounts=50,
        max_active_strategies=200,
        strategy_lab_access=True,
        ai_copilot_queries_per_day=10000,
        tick_level_history_access=True,
        sla_support_tier="DEDICATED_SLA",
        features=[
            "Everything in Autonomous Pro",
            "Dedicated VPS deployment with custom domain & reverse proxy",
            "Multi-tenant sub-account provisioning with strict tenant isolation",
            "Custom risk governor policy overrides (within safety floor invariants)",
            "Direct engineering channel & bespoke strategy verification",
        ],
    ),
}


class BillingEngine:
    """Manages subscription entitlements and transparent zero-charge launch period."""

    def __init__(self, is_launch_period: bool = True):
        self.is_launch_period = is_launch_period
        self._user_subscriptions: Dict[str, str] = {}  # tenant_id -> plan_id

    def list_available_plans(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in CANONICAL_PLANS.values()]

    def get_tenant_billing_status(self, tenant_id: str) -> Dict[str, Any]:
        plan_id = self._user_subscriptions.get(tenant_id, "AUTONOMOUS")
        plan = CANONICAL_PLANS.get(plan_id, CANONICAL_PLANS["AUTONOMOUS"])
        return {
            "tenant_id": tenant_id,
            "current_plan": plan.to_dict(),
            "is_launch_period": self.is_launch_period,
            "current_charge_usd": 0.00,
            "billing_status": "ACTIVE_FREE_LAUNCH_PERIOD",
            "expiry_date": "2027-10-01T00:00:00Z",  # 1 full year free
            "days_remaining_in_free_period": 358,
            "fee_schedule_disclosure": {
                "maker_fee_pct": 0.0,
                "taker_fee_pct": 0.0,
                "platform_execution_fee_pct": 0.0,
                "hidden_percentage_deduction": 0.0,
            },
            "payment_methods_configured": 0,
            "charges_enabled": False,
        }

    def assign_plan(self, tenant_id: str, plan_tier: str) -> Dict[str, Any]:
        tier_upper = plan_tier.upper()
        if tier_upper not in CANONICAL_PLANS:
            raise ValueError(f"Unknown plan tier '{plan_tier}'. Available: {list(CANONICAL_PLANS.keys())}")
        self._user_subscriptions[tenant_id] = tier_upper
        logger.info(f"Assigned plan {tier_upper} to tenant {tenant_id} (Charges: $0.00 launch)")
        return self.get_tenant_billing_status(tenant_id)
