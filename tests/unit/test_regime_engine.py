"""
Unit tests for Market Intelligence Regime Engine.
"""

import pytest
import numpy as np
from market_intelligence.regime_engine import (
    MarketRegimeEngine,
    TrendRegime,
    VolatilityRegime,
    RegimeFilterAction,
)


def test_regime_classification_strong_bull_and_expansion():
    # Construct upward trending price series
    t = np.arange(100)
    closes = 100.0 + t * 2.0  # Steady uptrend
    highs = closes + 1.5
    lows = closes - 1.5

    regime = MarketRegimeEngine.classify_regime(
        timestamp=1000,
        symbol="BTCUSDT",
        closes=closes,
        highs=highs,
        lows=lows,
    )
    assert regime.trend_regime in (TrendRegime.STRONG_BULL, TrendRegime.WEAK_BULL)
    assert regime.ema_alignment_score > 0

    # Compatibility with MTF Continuation (FAM-07)
    compat_trend = MarketRegimeEngine.evaluate_strategy_compatibility(
        strategy_family_id="FAM-07",
        regime=regime,
        signal_direction="LONG",
    )
    assert compat_trend.action in (RegimeFilterAction.ALLOW_FULL_SIZE, RegimeFilterAction.ALLOW_HALF_SIZE)
    assert compat_trend.compatibility_score >= 0.70

    # Incompatibility with Counter-Trend Short
    compat_counter = MarketRegimeEngine.evaluate_strategy_compatibility(
        strategy_family_id="FAM-07",
        regime=regime,
        signal_direction="SHORT",
    )
    assert compat_counter.action == RegimeFilterAction.SUPPRESS_SIGNAL
    assert compat_counter.compatibility_score < 0.45
