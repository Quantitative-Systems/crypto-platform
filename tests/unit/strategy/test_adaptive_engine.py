"""Unit Tests for Immutable AdaptiveEngineV1."""
import pytest
from market_model.contracts import (
    KeyZone,
    LiquidityPool,
    LiquidityType,
    MarketPhaseType,
    MarketState,
    PhaseSnapshot,
    StructuralBreak,
    StructuralBreakType,
    StructureSnapshot,
    SwingPoint,
    TrendDirection,
    ZonesSnapshot,
)
from strategy.adaptive.adaptive_engine_v1 import (
    AdaptiveEngineV1,
    AdaptiveMarketState,
)


def test_adaptive_engine_state_classification():
    engine = AdaptiveEngineV1(
        timeframe_set_id="SET_2", htf_label="1w", mtf_label="1d", ltf_label="4h"
    )

    # 1. Bullish Continuation
    htf_bull = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1w", close_price=60000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
    )
    mtf_cont = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1d", close_price=61000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BULLISH),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONTINUATION),
    )
    assert engine.classify_market_state(htf_bull, mtf_cont) == AdaptiveMarketState.BULL_TRENDING_CONTINUATION

    # 2. Ranging Chop Filter
    mtf_side = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1d", close_price=60000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.RANGE),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONSOLIDATION, is_compressed=True),
    )
    assert engine.classify_market_state(htf_bull, mtf_side) == AdaptiveMarketState.RANGING_CHOP

    # 3. Bearish Pullback Filter
    htf_bear = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1w", close_price=40000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BEARISH),
    )
    mtf_pull = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1d", close_price=42000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.BEARISH),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.PULLBACK),
    )
    assert engine.classify_market_state(htf_bear, mtf_pull) == AdaptiveMarketState.BEAR_PULLBACK


def test_adaptive_engine_no_trade_in_chop():
    engine = AdaptiveEngineV1(
        timeframe_set_id="SET_2", htf_label="1w", mtf_label="1d", ltf_label="4h"
    )

    htf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1w", close_price=50000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.RANGE),
    )
    mtf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="1d", close_price=50000.0,
        structure=StructureSnapshot(external_trend=TrendDirection.RANGE),
        phase=PhaseSnapshot(current_phase=MarketPhaseType.CONSOLIDATION),
    )
    ltf = MarketState(
        symbol="BTCUSDT", timestamp_ms=1000, timeframe="4h", close_price=50000.0,
    )

    sig, audit = engine.evaluate_adaptive_decision(0, 1000, htf, mtf, ltf)
    assert sig is None
    assert audit.action == "NO_TRADE"
    assert "REASON_CHOP_FILTER" in audit.reason
