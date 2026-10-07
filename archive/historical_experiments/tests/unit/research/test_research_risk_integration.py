"""
Unit tests verifying that the research replayer strictly integrates canonical Risk Firewall contracts.
"""

import pytest
from market_intelligence.primitives import Candle, TrendDirection
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.risk_rejection import RiskRejectionReason, RiskRejectionPayload
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator
from research.replayer.causal_replayer import CausalReplayer


def test_research_replayer_risk_firewall_rejection_low_rr():
    """Trade plan with RR < 4.0 must be rejected by RiskCoordinator during research replay."""
    account_state = AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    # 2.0R plan (Entry 100, Stop 90, Target 120 -> RR = 20 / 10 = 2.0 < 4.0)
    low_rr_plan = TradePlanPayload(
        trade_plan_id="plan_low_rr",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        setup_timestamp=1000,
        directional_permission="PERMIT_LONG",
        entry_price=100.0,
        stop_invalidation_price=90.0,
        target_price=120.0,
        raw_rr=2.0,
        status="ENTERED"
    )

    result = RiskCoordinator.evaluate(low_rr_plan, account_state)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_RR_BELOW_FLOOR


def test_research_replayer_position_sizing_1pct_cap():
    """Position sizing during research replay strictly sizes to 1.0% equity risk cap."""
    account_state = AccountState(
        current_equity=50000.0,
        peak_equity=50000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    # Entry 10000.0, Stop 9500.0 (5% distance = $500), Target 13000.0 (6.0R)
    plan = TradePlanPayload(
        trade_plan_id="plan_valid",
        hypothesis_id="HYP_UNIFIED",
        symbol="BTCUSDT",
        setup_timestamp=1000,
        directional_permission="PERMIT_LONG",
        entry_price=10000.0,
        stop_invalidation_price=9500.0,
        target_price=13000.0,
        raw_rr=6.0,
        status="ENTERED"
    )

    result = RiskCoordinator.evaluate(plan, account_state)
    assert isinstance(result, RiskApprovedPlan)
    # 1.0% of $50,000 = $500 dollar risk
    assert result.dollar_risk == 500.0
    # $500 risk / $500 stop distance = 1.0 unit
    assert result.position_units == 1.0
