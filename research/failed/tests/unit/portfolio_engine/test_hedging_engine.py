"""
Unit tests for QCP PortfolioHedgingEngine.
"""

import pytest
from portfolio_engine.hedging_engine import (
    PortfolioHedgingEngine,
    PositionExposure,
    HedgeAction,
    HedgingDecision
)


def test_hedging_engine_no_hedge_needed():
    engine = PortfolioHedgingEngine(max_allowable_beta=2.0, max_portfolio_heat_pct=3.0)
    positions = [
        PositionExposure(symbol="BTC/USDT", direction="LONG", notional_usd=500.0, risk_usd=50.0)
    ]
    decision = engine.evaluate_hedge_requirement(positions, account_equity=10_000.0)
    assert decision.action == HedgeAction.NO_HEDGE_NEEDED
    assert decision.net_portfolio_beta == 0.05
    assert decision.total_portfolio_heat_pct == 0.5


def test_hedging_engine_triggers_on_excessive_beta():
    engine = PortfolioHedgingEngine(max_allowable_beta=1.5, max_portfolio_heat_pct=3.0)
    # High leverage long SOL + ETH
    positions = [
        PositionExposure(symbol="SOL/USDT", direction="LONG", notional_usd=15_000.0, risk_usd=150.0),
        PositionExposure(symbol="ETH/USDT", direction="LONG", notional_usd=10_000.0, risk_usd=100.0)
    ]
    # Net beta = (15000*1.45 + 10000*1.15) / 10000 = (21750 + 11500)/10000 = 3.325 > 2.25
    decision = engine.evaluate_hedge_requirement(positions, account_equity=10_000.0, macro_regime_is_hostile=True)
    assert decision.action == HedgeAction.HEDGE_ACTIVE
    assert decision.target_hedge_notional > 0
    assert decision.recommended_hedge_symbol == "BTCUSDT"
