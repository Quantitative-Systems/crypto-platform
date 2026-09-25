"""Unit tests for the Quantitative Market Regime & Intelligence Engine."""
import numpy as np
import pytest

from crypto_platform.research_engine.regime_engine import MarketRegime, RegimeEngine


def test_regime_engine_short_series_fallback():
    engine = RegimeEngine(atr_lookback=10, trend_lookback=20)
    closes = np.array([100.0, 101.0, 102.0])
    highs = np.array([101.0, 102.0, 103.0])
    lows = np.array([99.0, 100.0, 101.0])

    state = engine.classify_series("BTCUSDT", closes, highs, lows)
    assert state.regime == MarketRegime.RANGING_COMPRESSED
    assert state.risk_multiplier == 1.0


def test_regime_engine_trending_bull_detection():
    engine = RegimeEngine(atr_lookback=10, trend_lookback=30)
    # Generate an upward trending series
    n = 60
    base = 100.0 + np.linspace(0, 30, n)
    highs = base + 1.0
    lows = base - 1.0
    closes = base

    state = engine.classify_series("ETHUSDT", closes, highs, lows, current_funding_bps=1.5)
    assert state.regime == MarketRegime.TRENDING_BULL
    assert state.trend_strength > 2.0
    assert state.recommended_allocation["trend"] >= 0.7


def test_regime_engine_liquidity_crisis_detection():
    engine = RegimeEngine(atr_lookback=10, trend_lookback=30)
    # Generate stable series followed by an extreme volatility spike
    n = 60
    closes = np.ones(n) * 100.0
    highs = np.ones(n) * 101.0
    lows = np.ones(n) * 99.0

    # Add extreme volatility in the last 10 bars
    highs[-10:] = 130.0
    lows[-10:] = 70.0
    closes[-10:] = 105.0

    state = engine.classify_series("SOLUSDT", closes, highs, lows)
    assert state.regime in [MarketRegime.LIQUIDITY_CRISIS, MarketRegime.VOLATILITY_EXPANSION]
    # In crisis/volatility expansion, risk multiplier should be clamped down
    assert state.risk_multiplier < 1.0


def test_compute_portfolio_regime_matrix():
    engine = RegimeEngine(atr_lookback=10, trend_lookback=30)
    n = 50
    data = {
        "BTCUSDT": {
            "closes": 100.0 + np.linspace(0, 20, n),
            "highs": 101.0 + np.linspace(0, 20, n),
            "lows": 99.0 + np.linspace(0, 20, n),
        },
        "ETHUSDT": {
            "closes": np.ones(n) * 2000.0,
            "highs": np.ones(n) * 2005.0,
            "lows": np.ones(n) * 1995.0,
        },
    }
    matrix = engine.compute_portfolio_regime_matrix(data, {"BTCUSDT": 1.0, "ETHUSDT": 0.5})
    assert "dominant_regime" in matrix
    assert "portfolio_risk_scale" in matrix
    assert len(matrix["symbols"]) == 2
