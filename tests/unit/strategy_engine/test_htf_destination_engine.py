"""
Unit tests for HTFDestinationEngine.
Verifies discovery of opposing keyzones, liquidity pools, weak swings, and geometry validation.
"""

import pytest
from market_intelligence.primitives import (
    MarketStatePayload,
    TrendDirection,
    KeyZone,
    EQHLiquidityPool,
    LiquidityPoolType,
    StructureState,
    SequenceSwing,
    RawSwing,
    SwingType
)
from market_intelligence.keyzone_engine import KeyZoneType, ZoneScope, ZoneStatus
from strategy_engine.context.htf_destination_engine import (
    HTFDestinationEngine,
    DestinationType
)


def _make_payload(
    trend=TrendDirection.BULLISH,
    current_price=100.0,
    keyzones=None,
    liquidity_pools=None,
    weak_swing_price=None
):
    struct = StructureState(
        sequence_swings=[],
        external_trend=trend,
        internal_trend=trend,
        protected_high=None,
        protected_low=None,
        weak_high=None,
        weak_low=None,
        dealing_range=None,
        events=[]
    )
    if weak_swing_price is not None:
        from market_intelligence.primitives import SequenceLabel
        st = SwingType.HIGH if trend == TrendDirection.BULLISH else SwingType.LOW
        label = SequenceLabel.HH if trend == TrendDirection.BULLISH else SequenceLabel.LL
        raw = RawSwing(
            swing_id="raw_weak",
            swing_type=st,
            price=weak_swing_price,
            candle_index=10,
            confirmation_index=12,
            timestamp=1000,
            confirmation_timestamp=1200
        )
        seq = SequenceSwing(raw_swing=raw, label=label)
        if trend == TrendDirection.BULLISH:
            struct.weak_high = seq
        else:
            struct.weak_low = seq

    return MarketStatePayload(
        symbol="BTCUSD",
        timeframe="1D",
        timestamp=1000,
        current_price=current_price,
        current_candle=None,
        events=[],
        swings=[],
        structure_state=struct,
        liquidity_pools=liquidity_pools or [],
        keyzones=keyzones or [],
        phase_state=None,
        trend_state=trend
    )


def test_opposing_keyzone_destination_bullish():
    # Long trade with current_price 100. Opposing keyzone (Bearish OB) at 120-125
    kz = KeyZone(
        zone_id="OB_BEARISH_1",
        zone_type="BEARISH_OB",
        direction=TrendDirection.BEARISH,
        high=125.0,
        low=120.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, keyzones=[kz])
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.OPPOSING_KEYZONE
    assert dest.target_price == 120.0  # Front edge of the resistance zone
    assert dest.source_id == "OB_BEARISH_1"


def test_liquidity_pool_destination():
    # Long trade with current_price 100. EQH at 115.0
    pool = EQHLiquidityPool(
        pool_id="EQH_1",
        pool_type=LiquidityPoolType.EQH,
        price_level=115.0,
        swings=[],
        is_swept=False
    )
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, liquidity_pools=[pool])
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.LIQUIDITY_POOL
    assert dest.target_price == 115.0


def test_weak_swing_destination():
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, weak_swing_price=130.0)
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.WEAK_SWING
    assert dest.target_price == 130.0


def test_invalid_geometry_rejected():
    # For Bullish, if target is below current price, reject
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, weak_swing_price=90.0)
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is False
    assert dest.target_price is None
    assert "REJECT" in dest.rejection_reason


def test_bearish_destination():
    # Short trade with current_price 100. Opposing keyzone (Bullish OB) at 80-85
    kz = KeyZone(
        zone_id="OB_BULLISH_1",
        zone_type="BULLISH_OB",
        direction=TrendDirection.BULLISH,
        high=85.0,
        low=80.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    payload = _make_payload(trend=TrendDirection.BEARISH, current_price=100.0, keyzones=[kz])
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.OPPOSING_KEYZONE
    assert dest.target_price == 85.0  # Front edge of support zone (high)

