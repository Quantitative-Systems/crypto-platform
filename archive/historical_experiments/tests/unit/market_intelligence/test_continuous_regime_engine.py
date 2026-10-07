"""
Tests for Continuous Multi-Dimensional Regime Engine.
"""

import pandas as pd
import numpy as np
from market_intelligence.continuous_regime_engine import (
    ContinuousRegimeEngine,
    RegimeState,
    TrendState,
    VolatilityState,
    LiquidityState,
    FundingState,
    CorrelationState,
)


def test_continuous_regime_classification():
    engine = ContinuousRegimeEngine()

    dates = pd.date_range("2024-01-01", periods=100, freq="4h", tz="UTC")
    # Upward trending prices
    c = 100.0 * np.exp(np.linspace(0, 0.20, len(dates)))
    h = c * 1.01
    l = c * 0.99
    o = c * 0.995
    v = np.full(len(dates), 5000.0)

    df = pd.DataFrame({"timestamp": dates, "open": o, "high": h, "low": l, "close": c, "volume": v})

    state = engine.classify_series(df, symbol="SOL/USDT", funding_rate_bps=1.5, cross_corr_score=0.40)
    assert isinstance(state, RegimeState)
    assert state.symbol == "SOL/USDT"
    assert state.trend in [TrendState.BULL_MOMENTUM, TrendState.SIDEWAYS_CHOP]
    assert state.volatility in [VolatilityState.LOW_VOL_SQUEEZE, VolatilityState.NORMAL_VOL, VolatilityState.VOL_EXPLOSION]
    assert state.liquidity in [LiquidityState.NORMAL_DEPTH, LiquidityState.EXPANDING_DEPTH]
    assert state.funding == FundingState.NEUTRAL_CARRY
    assert state.correlation == CorrelationState.DISPERSED_MARKET

    d = state.to_dict()
    assert "trend" in d
    assert "volatility_percentile" in d
