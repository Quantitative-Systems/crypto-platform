"""Unit Tests for Primary 4R/5R Hypothesis Engine."""
import numpy as np

from market_model.contracts import (
    KeyZone,
    MarketPhaseType,
    MarketState,
    MeasurementsSnapshot,
    PhaseSnapshot,
    StructureSnapshot,
    TrendDirection,
    ZonesSnapshot,
)
from research.experiments.primary_hypothesis import HypothesisConfig, PrimaryHypothesisEngine


def test_primary_hypothesis_long_setup():
    config = HypothesisConfig(min_target_r=4.0, allow_long=True, allow_short=True)
    engine = PrimaryHypothesisEngine(config)

    state = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1700000000000,
        timeframe="1D",
        close_price=60000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
        zones=ZonesSnapshot(premium_discount_zone="DISCOUNT"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.PULLBACK),
        measurements=MeasurementsSnapshot(atr=1000.0),
    )

    intent = engine.evaluate(state)
    assert intent is not None
    assert intent.direction == 1
    assert intent.target_r == 4.0
    # stop_dist = atr * 2.0 = 2000.0
    assert intent.stop_price == 58000.0  # 60000 - 2000
    assert intent.target_price == 68000.0  # 60000 + 4.0 * 2000


def test_primary_hypothesis_short_setup():
    config = HypothesisConfig(min_target_r=5.0, allow_long=True, allow_short=True)
    engine = PrimaryHypothesisEngine(config)

    state = MarketState(
        symbol="ETHUSDT",
        timestamp_ms=1700000000000,
        timeframe="1D",
        close_price=3000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BEARISH),
        zones=ZonesSnapshot(premium_discount_zone="PREMIUM"),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.PULLBACK),
        measurements=MeasurementsSnapshot(atr=50.0),
    )

    intent = engine.evaluate(state)
    assert intent is not None
    assert intent.direction == -1
    assert intent.target_r == 5.0
    # stop_dist = atr * 2.0 = 100.0
    assert intent.stop_price == 3100.0  # 3000 + 100
    assert intent.target_price == 2500.0  # 3000 - 5.0 * 100
