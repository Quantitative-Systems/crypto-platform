"""
Unit tests for Alpha RegimeFilter.
Verifies volatility compression and structural compression detection.
"""

import pytest
from market_intelligence.primitives import MarketStatePayload, Candle, MarketPhase, TrendDirection
from strategy_engine.classifiers.regime_filter import RegimeFilter, RegimeDecision
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator


def make_dummy_payload(phase: MarketPhase = MarketPhase.EXPANSION, trend: TrendDirection = TrendDirection.BULLISH) -> MarketStatePayload:
    c = Candle(timestamp=1000, open=100.0, high=105.0, low=95.0, close=102.0, volume=1000.0)
    return MarketStatePayload(
        symbol="BTCUSDT",
        timeframe="1D",
        timestamp=1000,
        current_price=102.0,
        current_candle=c,
        events=[],
        swings=[],
        structure_state=None,  # type: ignore
        liquidity_pools=[],
        keyzones=[],
        phase_state=phase,
        trend_state=trend
    )


def test_regime_filter_compression_phase():
    rf = RegimeFilter(enable_filter=True)
    payload = make_dummy_payload(phase=MarketPhase.COMPRESSION)
    decision = rf.evaluate(payload)
    
    assert not decision.is_permitted
    assert decision.regime_label == "COMPRESSION_PHASE"
    assert "COMPRESSION" in decision.reason


def test_regime_filter_healthy_volatility():
    rf = RegimeFilter(min_volatility_ratio=0.65, atr_period_short=5, atr_period_long=10, enable_filter=True)
    payload = make_dummy_payload(phase=MarketPhase.EXPANSION)
    
    # Create 20 candles with consistent volatility
    candles = [
        Candle(timestamp=i * 60, open=100.0, high=110.0, low=90.0, close=105.0, volume=100.0)
        for i in range(20)
    ]
    decision = rf.evaluate(payload, candles)
    assert decision.is_permitted
    assert decision.regime_label == "HEALTHY_VOLATILITY"
    assert decision.volatility_ratio >= 0.65


def test_regime_filter_volatility_squeeze():
    rf = RegimeFilter(min_volatility_ratio=0.70, atr_period_short=5, atr_period_long=15, enable_filter=True)
    payload = make_dummy_payload(phase=MarketPhase.EXPANSION)
    
    # Create 10 wide candles then 5 extremely narrow candles (squeeze)
    candles = [
        Candle(timestamp=i * 60, open=100.0, high=120.0, low=80.0, close=100.0, volume=100.0)
        for i in range(10)
    ] + [
        Candle(timestamp=(10 + i) * 60, open=100.0, high=101.0, low=99.0, close=100.0, volume=10.0)
        for i in range(5)
    ]
    decision = rf.evaluate(payload, candles)
    assert not decision.is_permitted
    assert decision.regime_label == "VOLATILITY_SQUEEZE"
    assert decision.volatility_ratio < 0.70


def test_strategy_coordinator_respects_regime_filter():
    rf = RegimeFilter(enable_filter=True)
    coord = StrategyCoordinator(enable_mtf_trailing=True, enable_profit_lock=True, regime_filter=rf)
    
    # If HTF is in compression phase, no new candidates should be spawned
    htf = make_dummy_payload(phase=MarketPhase.COMPRESSION, trend=TrendDirection.BULLISH)
    mtf = make_dummy_payload(phase=MarketPhase.EXPANSION, trend=TrendDirection.BULLISH)
    ltf = make_dummy_payload(phase=MarketPhase.EXPANSION, trend=TrendDirection.BULLISH)
    
    plans = coord.evaluate(htf, mtf, ltf)
    assert len(plans) == 0
    assert len(coord.candidate_tracker.get_active_candidates("BTCUSDT", "UNIFIED_STRATEGY")) == 0
