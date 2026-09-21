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
    # Bullish OB below current price acts as demand/support target
    payload = _make_payload(trend=TrendDirection.BEARISH, current_price=100.0, keyzones=[kz])
    dest = HTFDestinationEngine.evaluate(payload)

    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.OPPOSING_KEYZONE
    assert dest.target_price == 85.0  # Front edge of support zone (high)


def test_forward_expansion_negative_price_rejected():
    from market_intelligence.primitives import DealingRange
    # Case replicating SOL trade #8: low=39.93, high=94.55 -> expansion target would be -14.69
    dr = DealingRange(high_price=94.55, low_price=39.93)
    payload = _make_payload(trend=TrendDirection.BEARISH, current_price=38.0)
    payload.structure_state.dealing_range = dr

    dest = HTFDestinationEngine.evaluate(payload, enable_forward_expansion=True)
    # Negative target -14.69 must be strictly rejected
    assert dest.is_valid is False
    assert dest.target_price is None
    assert dest.rejection_reason == "REJECT_NO_FORWARD_STRUCTURAL_DESTINATION"


def test_forward_expansion_positive_price_accepted():
    from market_intelligence.primitives import DealingRange
    # Valid positive expansion target: low=80, high=100, width=20 -> target = 60.0 (< current 75.0)
    dr = DealingRange(high_price=100.0, low_price=80.0)
    payload = _make_payload(trend=TrendDirection.BEARISH, current_price=75.0)
    payload.structure_state.dealing_range = dr

    dest = HTFDestinationEngine.evaluate(payload, enable_forward_expansion=True)
    assert dest.is_valid is True
    assert dest.destination_type == DestinationType.FORWARD_STRUCTURAL_EXPANSION
    assert dest.target_price == 60.0
    assert dest.target_price > 0.0


def test_non_positive_keyzone_target_rejected():
    # If a keyzone has invalid high/low <= 0.0, it must not be selected as target
    kz = KeyZone(
        zone_id="OB_INVALID_NEG",
        zone_type="BULLISH_OB",
        direction=TrendDirection.BULLISH,
        high=-5.0,
        low=-10.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    payload = _make_payload(trend=TrendDirection.BEARISH, current_price=10.0, keyzones=[kz])
    dest = HTFDestinationEngine.evaluate(payload)
    assert dest.is_valid is False
    assert dest.target_price is None


def test_target_hierarchy_mode_structural_objective():
    # Bullish setup:
    # Nearer KeyZone at 105.0
    # Farther Weak High at 130.0
    kz = KeyZone(
        zone_id="OB_BEARISH_NEAR",
        zone_type="BEARISH_OB",
        direction=TrendDirection.BEARISH,
        high=110.0,
        low=105.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, keyzones=[kz], weak_swing_price=130.0)

    # Under CLOSEST_OBJECTIVE (baseline): selects nearer KeyZone
    dest_closest = HTFDestinationEngine.evaluate(payload, hierarchy_mode="CLOSEST_OBJECTIVE")
    assert dest_closest.is_valid is True
    assert dest_closest.destination_type == DestinationType.OPPOSING_KEYZONE
    assert dest_closest.target_price == 105.0

    # Under STRUCTURAL_OBJECTIVE (experiment): selects major directional Weak Swing
    dest_struct = HTFDestinationEngine.evaluate(payload, hierarchy_mode="STRUCTURAL_OBJECTIVE")
    assert dest_struct.is_valid is True
    assert dest_struct.destination_type == DestinationType.WEAK_SWING
    assert dest_struct.target_price == 130.0


def test_target_hierarchy_liquidity_pool_over_keyzone():
    # Bullish setup:
    # Nearer KeyZone at 105.0
    # Farther Liquidity Pool at 120.0
    kz = KeyZone(
        zone_id="OB_BEARISH_NEAR",
        zone_type="BEARISH_OB",
        direction=TrendDirection.BEARISH,
        high=110.0,
        low=105.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    pool = EQHLiquidityPool(
        pool_id="EQH_MAJOR",
        pool_type=LiquidityPoolType.EQH,
        price_level=120.0,
        swings=[],
        is_swept=False
    )
    payload = _make_payload(trend=TrendDirection.BULLISH, current_price=100.0, keyzones=[kz], liquidity_pools=[pool])

    # Under STRUCTURAL_OBJECTIVE: selects Liquidity Pool over KeyZone
    dest_struct = HTFDestinationEngine.evaluate(payload, hierarchy_mode="STRUCTURAL_OBJECTIVE")
    assert dest_struct.is_valid is True
    assert dest_struct.destination_type == DestinationType.LIQUIDITY_POOL
    assert dest_struct.target_price == 120.0


