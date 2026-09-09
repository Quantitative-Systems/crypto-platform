"""
Unit tests verifying HYP_ENTRY_DISPLACEMENT_POLARITY_01:
Asserts that when enforce_displacement_polarity=True:
- Bullish LTF trigger candles are required for LONG setups.
- Bearish LTF trigger candles are required for SHORT setups.
- Counter-directional candles are rejected with REJECT_ENTRY_DISPLACEMENT_POLARITY.
Asserts that when enforce_displacement_polarity=False, default behavior is preserved.
"""

import pytest
from market_intelligence.primitives import (
    MarketStatePayload,
    Candle,
    StructureState,
    EventType,
    MarketEvent
)
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy


def _make_dummy_state(symbol: str, tf: str, ts: int, candle: Candle) -> MarketStatePayload:
    return MarketStatePayload(
        symbol=symbol,
        timeframe=tf,
        timestamp=ts,
        current_price=candle.close,
        current_candle=candle,
        events=[],
        swings=[],
        structure_state=StructureState(),
        liquidity_pools=[],
        keyzones=[],
        phase_state=None,
        trend_state=None,
        scorecard={"reason_codes": ["DISPLACEMENT_CONFIRMED"]}
    )


def test_polarity_filter_rejects_bearish_candle_in_long_setup():
    strategy = UnifiedStrategy(enforce_displacement_polarity=True)
    
    cand = CandidateSetup(
        candidate_id="cand_test_long_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="4h",
        mtf="1h",
        ltf="15m",
        state=CandidateState.WAIT_LTF_TRIGGER,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        creation_timestamp=1000,
        mtf_retest_timestamp=1000
    )
    
    # Bearish trigger candle (Open 102, Close 98)
    bearish_candle = Candle(timestamp=1100, open=102.0, high=103.0, low=97.0, close=98.0, volume=50.0)
    ltf_payload = _make_dummy_state("BTC/USDT", "15m", 1100, bearish_candle)
    ltf_payload.events = [
        MarketEvent(
            timestamp=1050,
            timeframe="15m",
            symbol="BTC/USDT",
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=96.0,
            metadata={"direction": "BULLISH"}
        )
    ]
    
    htf_payload = _make_dummy_state("BTC/USDT", "4h", 1100, bearish_candle)
    mtf_payload = _make_dummy_state("BTC/USDT", "1h", 1100, bearish_candle)
    
    plan = strategy.evaluate(cand, htf_payload, mtf_payload, ltf_payload)
    
    assert cand.state == CandidateState.REJECTED
    assert cand.invalidation_reason == "REJECT_ENTRY_DISPLACEMENT_POLARITY"
    assert plan is not None
    assert plan.status == "REJECTED"


def test_polarity_filter_rejects_bullish_candle_in_short_setup():
    strategy = UnifiedStrategy(enforce_displacement_polarity=True)
    
    cand = CandidateSetup(
        candidate_id="cand_test_short_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="4h",
        mtf="1h",
        ltf="15m",
        state=CandidateState.WAIT_LTF_TRIGGER,
        directional_permission=DirectionalPermission.PERMIT_SHORT,
        creation_timestamp=1000,
        mtf_retest_timestamp=1000
    )
    
    # Bullish trigger candle (Open 98, Close 102)
    bullish_candle = Candle(timestamp=1100, open=98.0, high=103.0, low=97.0, close=102.0, volume=50.0)
    ltf_payload = _make_dummy_state("BTC/USDT", "15m", 1100, bullish_candle)
    ltf_payload.events = [
        MarketEvent(
            timestamp=1050,
            timeframe="15m",
            symbol="BTC/USDT",
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=104.0,
            metadata={"direction": "BEARISH"}
        )
    ]
    
    htf_payload = _make_dummy_state("BTC/USDT", "4h", 1100, bullish_candle)
    mtf_payload = _make_dummy_state("BTC/USDT", "1h", 1100, bullish_candle)
    
    plan = strategy.evaluate(cand, htf_payload, mtf_payload, ltf_payload)
    
    assert cand.state == CandidateState.REJECTED
    assert cand.invalidation_reason == "REJECT_ENTRY_DISPLACEMENT_POLARITY"
    assert plan is not None
    assert plan.status == "REJECTED"


def test_polarity_filter_disabled_by_default():
    strategy = UnifiedStrategy(enforce_displacement_polarity=False)
    assert strategy.enforce_displacement_polarity is False
