"""
Unit tests for Family 9 Relative Value Alpha & Hedging Engine.
"""

import pytest
import numpy as np
from research.discovery_lab.family_09_relative_value import RelativeValueAlphaEngine, PairTrade
from portfolio_engine.hedging_engine import (
    PortfolioHedgingEngine,
    HedgeAction,
    PositionExposure,
)
from market_intelligence.primitives import Candle


def test_relative_value_pair_alignment():
    candles_a = [
        Candle(timestamp=100, open=10, high=12, low=9, close=11, volume=100),
        Candle(timestamp=200, open=11, high=13, low=10, close=12, volume=100),
        Candle(timestamp=300, open=12, high=14, low=11, close=13, volume=100),
    ]
    candles_b = [
        Candle(timestamp=100, open=20, high=22, low=19, close=21, volume=100),
        Candle(timestamp=200, open=21, high=23, low=20, close=22, volume=100),
        Candle(timestamp=400, open=22, high=24, low=21, close=23, volume=100),
    ]

    ts, p_a, p_b = RelativeValueAlphaEngine.align_pair_candles(candles_a, candles_b)
    # Only ts 100 and 200 overlap
    assert len(ts) == 2
    assert list(ts) == [100, 200]
    assert list(p_a) == [11, 12]
    assert list(p_b) == [21, 22]


def test_hedging_engine_hedge_unavailable_on_small_capital():
    engine = PortfolioHedgingEngine(max_allowable_beta=0.8, max_portfolio_heat_pct=3.0)
    # Open positions on a $10 account
    positions = [
        PositionExposure(symbol="SOLUSDT", direction="LONG", notional_usd=4.0, risk_usd=0.15),
        PositionExposure(symbol="ETHUSDT", direction="LONG", notional_usd=3.0, risk_usd=0.15),
    ]
    # Net beta will be elevated (>0.8): (4/10 * 1.45) + (3/10 * 1.15) = 0.58 + 0.345 = 0.925
    decision = engine.evaluate_hedge_requirement(
        open_positions=positions,
        account_equity=10.0,
        macro_regime_is_hostile=True,
    )
    # The target hedge notional is small (~$1-2), below $5.00 min notional
    assert decision.action == HedgeAction.HEDGE_UNAVAILABLE
    assert "below exchange minimum" in decision.reason


def test_hedging_engine_active_on_large_capital():
    engine = PortfolioHedgingEngine(max_allowable_beta=1.5, max_portfolio_heat_pct=3.0)
    # Open positions on a $10,000 account
    positions = [
        PositionExposure(symbol="SOLUSDT", direction="LONG", notional_usd=10000.0, risk_usd=150.0),
        PositionExposure(symbol="ETHUSDT", direction="LONG", notional_usd=10000.0, risk_usd=150.0),
    ]
    decision = engine.evaluate_hedge_requirement(
        open_positions=positions,
        account_equity=10000.0,
        macro_regime_is_hostile=True,
    )
    assert decision.action == HedgeAction.HEDGE_ACTIVE
    assert decision.executable_hedge_notional >= engine.MIN_EXCHANGE_NOTIONAL
