"""
Unit tests for MTFStructuralTrailingEngine.
Verifies monotonic structural ratcheting behind confirmed swings and immediate exit on adverse MTF CHOCH.
"""

import pytest
from market_intelligence.primitives import (
    MarketStatePayload,
    TrendDirection,
    StructureState,
    StructureEvent,
    EventType,
    SequenceSwing,
    RawSwing,
    SwingType,
    SequenceLabel
)
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.lifecycle.mtf_trailing_engine import (
    MTFStructuralTrailingEngine,
    TrailingDecision
)


def _make_trade_plan(is_long=True, entry_price=100.0, initial_sl=90.0, target_price=150.0, setup_ts=1000):
    return TradePlanPayload(
        trade_plan_id="trade_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        directional_permission=DirectionalPermission.PERMIT_LONG.value if is_long else DirectionalPermission.PERMIT_SHORT.value,
        setup_timestamp=setup_ts,
        entry_price=entry_price,
        stop_invalidation_price=initial_sl,
        target_price=target_price,
        raw_rr=5.0,
        status="ENTERED",
        source_timeframes={"HTF": "1D", "MTF": "4H", "LTF": "1H"}
    )


def test_monotonic_trailing_behind_mtf_higher_low():
    plan = _make_trade_plan(is_long=True, entry_price=100.0, initial_sl=90.0)

    # MTF forms a new confirmed swing low at 96.0 at timestamp 1500 (> setup_ts 1000)
    raw = RawSwing("sw_mtf_1", 1500, 96.0, SwingType.LOW, 5, 1500, 6)
    seq = SequenceSwing(raw_swing=raw, label=SequenceLabel.HL)
    struct = StructureState(
        external_trend=TrendDirection.BULLISH,
        internal_trend=TrendDirection.BULLISH,
        sequence_swings=[seq],
        events=[]
    )
    mtf_payload = MarketStatePayload(
        symbol="BTCUSD", timeframe="4H", timestamp=1600, current_price=110.0,
        current_candle=None, events=[], swings=[], structure_state=struct,
        liquidity_pools=[], keyzones=[], phase_state=None, trend_state=TrendDirection.BULLISH
    )

    dec = MTFStructuralTrailingEngine.evaluate(plan, mtf_payload)
    assert dec.should_update_stop is True
    assert dec.new_stop_price == 96.0
    assert dec.should_exit_structural is False


def test_adverse_mtf_choch_triggers_exit():
    plan = _make_trade_plan(is_long=True, entry_price=100.0, initial_sl=90.0, setup_ts=1000)

    # MTF experiences a Bearish CHOCH at timestamp 1500 (> setup_ts 1000)
    choch_ev = StructureEvent(
        event_type=EventType.EXTERNAL_CHOCH,
        timestamp=1500,
        price_level=95.0,
        direction="BEARISH",
        broken_swing_id="sw_old",
        candle_index=10
    )
    struct = StructureState(
        external_trend=TrendDirection.BEARISH,
        internal_trend=TrendDirection.BEARISH,
        sequence_swings=[],
        events=[choch_ev]
    )
    mtf_payload = MarketStatePayload(
        symbol="BTCUSD", timeframe="4H", timestamp=1600, current_price=98.0,
        current_candle=None, events=[choch_ev], swings=[], structure_state=struct,
        liquidity_pools=[], keyzones=[], phase_state=None, trend_state=TrendDirection.BEARISH
    )

    dec = MTFStructuralTrailingEngine.evaluate(plan, mtf_payload)
    assert dec.should_exit_structural is True
    assert "BEARISH" in dec.exit_reason


def test_historical_choch_prior_to_setup_is_ignored():
    # CHOCH at timestamp 500 occurred BEFORE setup_ts 1000: must be ignored
    plan = _make_trade_plan(is_long=True, entry_price=100.0, initial_sl=90.0, setup_ts=1000)

    old_choch = StructureEvent(
        event_type=EventType.EXTERNAL_CHOCH,
        timestamp=500,
        price_level=95.0,
        direction="BEARISH",
        broken_swing_id="sw_ancient",
        candle_index=2
    )
    struct = StructureState(
        external_trend=TrendDirection.BULLISH,
        internal_trend=TrendDirection.BULLISH,
        sequence_swings=[],
        events=[old_choch]
    )
    mtf_payload = MarketStatePayload(
        symbol="BTCUSD", timeframe="4H", timestamp=1200, current_price=105.0,
        current_candle=None, events=[old_choch], swings=[], structure_state=struct,
        liquidity_pools=[], keyzones=[], phase_state=None, trend_state=TrendDirection.BULLISH
    )

    dec = MTFStructuralTrailingEngine.evaluate(plan, mtf_payload)
    assert dec.should_exit_structural is False
