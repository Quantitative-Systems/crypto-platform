"""
Unit Tests for Family 06: Volatility Expansion Squeeze Strategy.
Verifies pure NumPy indicator mechanics, squeeze state detection,
signal generation, and canonical strategy spec conformity.
"""

import pytest
import numpy as np

from research.discovery_lab.specs.fam06_volatility_squeeze import (
    bollinger_bands_numpy,
    keltner_channels_numpy,
    atr_numpy,
    compute_volatility_squeeze_signals,
    create_fam06_spec,
)
from platform_core.canonical_strategy_spec import StrategyLifecycleState


def test_bollinger_bands_geometry():
    np.random.seed(42)
    prices = 100.0 + np.cumsum(np.random.randn(100) * 0.5)
    mid, upper, lower = bollinger_bands_numpy(prices, period=20, num_std=2.0)

    assert len(mid) == 100
    assert len(upper) == 100
    assert len(lower) == 100

    # From index 19 onward, upper > mid > lower
    for i in range(19, 100):
        assert upper[i] >= mid[i]
        assert mid[i] >= lower[i]


def test_keltner_channels_geometry():
    np.random.seed(42)
    close = 100.0 + np.cumsum(np.random.randn(100) * 0.5)
    high = close + np.abs(np.random.randn(100) * 0.8)
    low = close - np.abs(np.random.randn(100) * 0.8)

    mid, upper, lower = keltner_channels_numpy(high, low, close, period=20, atr_period=14, atr_multiplier=1.5)

    assert len(mid) == 100
    for i in range(20, 100):
        assert upper[i] > mid[i]
        assert mid[i] > lower[i]


def test_volatility_squeeze_detection():
    """
    Creates a synthetic price series with high volatility, then extreme consolidation (squeeze),
    then strong upside breakout. Asserts squeeze fired and produced long signal.
    """
    n = 150
    # 0 to 50: random walk
    np.random.seed(123)
    p = [100.0]
    for _ in range(49):
        p.append(p[-1] + np.random.randn() * 1.5)

    # 50 to 90: tight consolidation around 100 (narrow range -> squeeze on)
    for _ in range(40):
        p.append(100.0 + np.random.randn() * 0.05)

    # 91 to 149: strong rally to 120 (breakout -> squeeze fires)
    for _ in range(58):
        p.append(p[-1] + 0.4 + np.random.randn() * 0.1)

    close = np.array(p, dtype=np.float64)
    high = close + 0.2
    low = close - 0.2

    longs, shorts, atr_vals = compute_volatility_squeeze_signals(
        high, low, close, bb_period=20, bb_std=2.0, kc_period=20, kc_mult=1.5
    )

    n = len(close)
    assert len(longs) == n
    assert len(shorts) == n
    # Long signal must trigger after the consolidation releases into expansion
    assert np.any(longs[90:110])


def test_canonical_fam06_spec_generation():
    spec = create_fam06_spec(
        symbol="SOLUSDT",
        timeframe_set=2,
        lifecycle_state=StrategyLifecycleState.RESEARCH,
    )
    assert spec.strategy_id == "FAM-06-VOLSQUEEZE_SOLUSDT_Set2"
    assert spec.family_id == "FAM-06-VOLSQUEEZE"
    assert spec.timeframes["LTF"] == "4H"
    assert spec.parameters["tp_r"] == 3.0
    assert spec.rules["collision_policy"] == "ADVERSE_FIRST"
    assert spec.validate() is True

    d = spec.to_dict()
    assert d["strategy_id"] == spec.strategy_id
    assert d["lifecycle_state"] == "RESEARCH"
