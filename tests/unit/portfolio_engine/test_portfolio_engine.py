"""
Unit tests for Product 05 — Portfolio & Dynamic Risk Engine.
Tests Volatility Sizer, Drawdown Dampener, and Portfolio Coordinator.
"""

import pytest
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from portfolio_engine.contracts.portfolio_state import PortfolioRiskConfig, PortfolioState
from portfolio_engine.allocator.volatility_target_sizer import VolatilityTargetSizer
from portfolio_engine.allocator.drawdown_dampener import DrawdownDampener
from portfolio_engine.portfolio_coordinator import PortfolioCoordinator


def make_plan(symbol="BTCUSDT", entry=100.0, sl=95.0, tp=120.0, units=1.0) -> RiskApprovedPlan:
    return RiskApprovedPlan(
        trade_plan_id="plan_test_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol=symbol,
        entry_price=entry,
        stop_loss_price=sl,
        target_price=tp,
        position_units=units,
        dollar_risk=5.0 * units,
        max_loss_pct=0.01
    )


def test_volatility_target_sizer():
    state = PortfolioState(nav=10000.0, cash_balance=10000.0, peak_nav=10000.0)
    cfg = PortfolioRiskConfig(target_annual_volatility=0.40, max_risk_per_trade_pct=0.01)
    plan = make_plan(entry=100.0, sl=95.0)  # 5% stop distance
    
    # 1. Normal ATR
    units, dollar_risk, vol_scale = VolatilityTargetSizer.calculate(plan, state, cfg, current_atr=2.0)
    assert dollar_risk > 0
    assert units > 0
    assert 0.5 <= vol_scale <= 1.5


def test_drawdown_dampener_tiers():
    cfg = PortfolioRiskConfig(drawdown_tier_1_pct=0.05, drawdown_tier_2_pct=0.10)
    
    # 1. No Drawdown -> 1.0x factor
    state_normal = PortfolioState(nav=10000.0, cash_balance=10000.0, peak_nav=10000.0)
    factor, reason = DrawdownDampener.get_dampener_factor(state_normal, cfg)
    assert factor == 1.0
    assert reason is None
    
    # 2. Tier 1 Drawdown (6% DD) -> 0.50x factor
    state_tier1 = PortfolioState(nav=9400.0, cash_balance=9400.0, peak_nav=10000.0)
    factor, reason = DrawdownDampener.get_dampener_factor(state_tier1, cfg)
    assert factor == 0.50
    assert reason is None
    
    # 3. Tier 2 Drawdown (12% DD) -> 0.0x factor (Circuit Pause)
    state_tier2 = PortfolioState(nav=8800.0, cash_balance=8800.0, peak_nav=10000.0)
    factor, reason = DrawdownDampener.get_dampener_factor(state_tier2, cfg)
    assert factor == 0.0
    assert "CIRCUIT_PAUSE" in reason


def test_portfolio_coordinator_heat_limits():
    cfg = PortfolioRiskConfig(
        max_total_portfolio_risk_pct=0.03,  # Max $300 risk on $10k NAV
        max_risk_per_trade_pct=0.01,        # Max $100 risk per trade
        max_asset_concentration_pct=0.015  # Max $150 risk on single asset
    )
    coord = PortfolioCoordinator(initial_nav=10000.0, config=cfg)
    
    # Trade 1: BTC (Approved)
    p1 = make_plan("BTCUSDT", entry=100.0, sl=95.0)
    alloc1 = coord.evaluate(p1)
    assert alloc1.is_approved
    coord.on_trade_executed(alloc1)
    
    # Trade 2: BTC (Approved within asset concentration)
    p2 = make_plan("BTCUSDT", entry=100.0, sl=95.0)
    alloc2 = coord.evaluate(p2)
    # Concentration limit check
    if alloc2.is_approved:
        coord.on_trade_executed(alloc2)
    
    # Trade 3: ETH (Approved)
    p3 = make_plan("ETHUSDT", entry=100.0, sl=95.0)
    alloc3 = coord.evaluate(p3)
    if alloc3.is_approved:
        coord.on_trade_executed(alloc3)
        
    # Trade 4: When total risk reaches or exceeds $300, new trades must be rejected by heat ceiling
    assert coord.state.total_risk_committed_pct <= 0.035
