"""Unit Tests for Canonical MarketState Contracts and Market Model Primitives."""
import numpy as np
import pytest

from market_model.contracts import MarketPhaseType, MarketState, TrendDirection
from market_model.key_zones_levels.order_blocks.key_zones_engine import KeyZonesEngine
from market_model.market_structure_trend.trend.structure_engine import StructureEngine
from market_model.phases.pullback.detection.phase_engine import PhaseEngine


def test_market_state_instantiation_and_serialization():
    state = MarketState(
        symbol="BTCUSDT",
        timestamp_ms=1700000000000,
        timeframe="1D",
        close_price=65000.0,
    )
    assert state.symbol == "BTCUSDT"
    assert state.structure.external_trend == TrendDirection.NEUTRAL
    
    serialized = state.to_dict()
    assert serialized["symbol"] == "BTCUSDT"
    assert serialized["structure"]["external_trend"] == "NEUTRAL"


def test_structure_engine_swings_and_breaks():
    engine = StructureEngine(timeframe="1D", major_left=2, major_right=2)
    
    # Synthetic bullish price sequence
    prices = np.array([100, 105, 110, 108, 107, 112, 120, 118, 115, 125, 130], dtype=float)
    highs = prices + 1.0
    lows = prices - 1.0
    closes = prices
    timestamps = np.arange(len(prices)) * 86400 * 1000

    snapshot = engine.compute_structure(prices, highs, lows, closes, timestamps)
    assert snapshot.last_major_high is not None or snapshot.last_major_low is not None


def test_key_zones_engine_fvg_detection():
    engine = KeyZonesEngine(fvg_min_bps=1.0)
    
    # Gap up: bar 0 high = 100, bar 2 low = 105 -> Bullish FVG
    opens = np.array([98, 102, 106], dtype=float)
    highs = np.array([100, 105, 110], dtype=float)
    lows = np.array([95, 101, 105], dtype=float)
    closes = np.array([99, 104, 109], dtype=float)
    timestamps = np.array([1000, 2000, 3000], dtype=np.int64)

    snapshot = engine.compute_zones(opens, highs, lows, closes, timestamps)
    assert len(snapshot.fair_value_gaps) == 1
    assert snapshot.fair_value_gaps[0].is_bullish is True
    assert snapshot.fair_value_gaps[0].low_price == 100.0
    assert snapshot.fair_value_gaps[0].high_price == 105.0


def test_phase_engine_pullback_classification():
    engine = PhaseEngine()
    struct_engine = StructureEngine(timeframe="1D", major_left=2, major_right=2)

    # Bullish market pullback scenario
    prices = np.array([100, 110, 120, 115, 112], dtype=float)
    highs = prices + 1.0
    lows = prices - 1.0
    timestamps = np.arange(len(prices)) * 86400 * 1000

    struct = struct_engine.compute_structure(prices, highs, lows, prices, timestamps)
    struct.external_trend = TrendDirection.BULLISH

    phase = engine.compute_phase(prices, highs, lows, struct)
    assert phase.current_phase in (MarketPhaseType.PULLBACK, MarketPhaseType.CONTINUATION, MarketPhaseType.UNCERTAIN)
