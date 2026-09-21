"""
Unit tests for PositionSizer friction boundary contract:
Canonical rule: maximum permitted friction (fees + slippage) <= 20% of dollar risk (worst_case_loss <= 1.20 * dollar_risk).
"""

import pytest
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.risk_rejection import RiskRejectionReason
from risk_engine.sizing.position_sizer import PositionSizer


@pytest.fixture
def base_account():
    return AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )


@pytest.fixture
def high_leverage_config():
    # max_leverage high enough to isolate the friction check
    return RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=0.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False,
        max_leverage=50.0,
        min_stop_distance_pct=0.001,
        quantity_step_size=0.0001
    )


def test_friction_below_20_percent_approved(base_account, high_leverage_config):
    """
    Stop distance = 0.60% ($60 on $10,000 entry).
    Notional = $16,666.67.
    Friction (10 bps total) = $16.67 (16.67% of $100 risk).
    Worst-case loss = $116.67 <= $120.0 -> Approved.
    """
    plan = TradePlanPayload(
        trade_plan_id="plan_f1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        setup_timestamp=1000000,
        directional_permission="PERMIT_LONG",
        entry_price=10000.0,
        stop_invalidation_price=9940.0,
        target_price=12000.0,
        raw_rr=34.33,
        status="ENTERED"
    )
    units, dollar_risk, rejection = PositionSizer.calculate(plan, base_account, high_leverage_config)
    assert rejection is None
    assert dollar_risk == 100.0
    assert units is not None and units > 0


def test_friction_exactly_20_percent_approved(base_account, high_leverage_config):
    """
    Stop distance = 0.50% ($50 on $10,000 entry).
    Notional = $20,000.0.
    Friction (10 bps total) = $20.00 (exactly 20.0% of $100 risk).
    Worst-case loss = $120.00 <= $120.0 -> Approved.
    """
    plan = TradePlanPayload(
        trade_plan_id="plan_f2",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        setup_timestamp=1000000,
        directional_permission="PERMIT_LONG",
        entry_price=10000.0,
        stop_invalidation_price=9950.0,
        target_price=12000.0,
        raw_rr=41.0,
        status="ENTERED"
    )
    units, dollar_risk, rejection = PositionSizer.calculate(plan, base_account, high_leverage_config)
    assert rejection is None
    assert dollar_risk == 100.0
    assert units is not None and units > 0


def test_friction_above_20_percent_rejected(base_account, high_leverage_config):
    """
    Stop distance = 0.40% ($40 on $10,000 entry).
    Notional = $25,000.0.
    Friction (10 bps total) = $25.00 (25.0% of $100 risk > 20.0%).
    Worst-case loss = $125.00 > $120.0 -> Rejected.
    """
    plan = TradePlanPayload(
        trade_plan_id="plan_f3",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        setup_timestamp=1000000,
        directional_permission="PERMIT_LONG",
        entry_price=10000.0,
        stop_invalidation_price=9960.0,
        target_price=12000.0,
        raw_rr=51.0,
        status="ENTERED"
    )
    units, dollar_risk, rejection = PositionSizer.calculate(plan, base_account, high_leverage_config)
    assert rejection == RiskRejectionReason.REJECT_FRICTION_ADJUSTED_RISK_VIOLATION
    assert units is None
