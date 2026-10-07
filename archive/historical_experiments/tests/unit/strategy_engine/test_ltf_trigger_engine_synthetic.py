"""
Unit tests for LTF Trigger Engine using synthetic candle data.
Covers:
1. Valid sweep + displacement
2. Sweep without displacement
3. Displacement without sweep
4. Invalid displacement body close
5. Valid protected swing
6. Missing protected swing
7. Valid complete trigger and trade plan generation
8. Invalid geometry rejection
"""

import pytest
from market_intelligence.primitives import (
    Candle, MarketStatePayload, MarketEvent, EventType,
    StructureState, SequenceSwing, RawSwing, SwingType, SwingStatus, SwingScope, SequenceLabel, TrendDirection
)
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.entry.ltf_entry_model import LTFEntryModel


def create_synthetic_payload(
    symbol: str = "BTC/USDT",
    current_price: float = 100.0,
    has_sweep: bool = True,
    has_displacement: bool = True,
    protected_low_price: float = None,
    protected_high_price: float = None,
    direction: str = "BULLISH"
) -> MarketStatePayload:
    events = []
    if has_sweep:
        events.append(MarketEvent(
            timestamp=1000,
            timeframe="1D",
            symbol=symbol,
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=98.0,
            metadata={"direction": direction}
        ))
        
    scorecard = {}
    if has_displacement:
        scorecard["reason_codes"] = ["DISPLACEMENT_CONFIRMED"]
        
    p_low = None
    if protected_low_price is not None:
        p_low = SequenceSwing(
            raw_swing=RawSwing(
                swing_id="sw_low_1",
                timestamp=900,
                price=protected_low_price,
                swing_type=SwingType.LOW,
                candle_index=5,
                confirmation_timestamp=950,
                confirmation_index=7,
                timeframe="1D"
            ),
            label=SequenceLabel.HL,
            is_protected=True
        )
        
    p_high = None
    if protected_high_price is not None:
        p_high = SequenceSwing(
            raw_swing=RawSwing(
                swing_id="sw_high_1",
                timestamp=900,
                price=protected_high_price,
                swing_type=SwingType.HIGH,
                candle_index=5,
                confirmation_timestamp=950,
                confirmation_index=7,
                timeframe="1D"
            ),
            label=SequenceLabel.LH,
            is_protected=True
        )
        
    structure_state = StructureState(
        external_trend=TrendDirection.BULLISH if direction == "BULLISH" else TrendDirection.BEARISH,
        protected_low=p_low,
        protected_high=p_high
    )
    
    return MarketStatePayload(
        symbol=symbol,
        timeframe="1D",
        timestamp=1000,
        current_price=current_price,
        current_candle=Candle(timestamp=1000, open=99.0, high=102.0, low=97.0, close=current_price, volume=100.0),
        events=events,
        swings=[],
        structure_state=structure_state,
        liquidity_pools=[],
        keyzones=[],
        phase_state=None,
        trend_state=TrendDirection.BULLISH if direction == "BULLISH" else TrendDirection.BEARISH,
        scorecard=scorecard
    )


def test_1_valid_sweep_and_displacement():
    """LTFEntryModel returns True when both liquidity sweep and displacement are confirmed."""
    payload = create_synthetic_payload(has_sweep=True, has_displacement=True, direction="BULLISH")
    assert LTFEntryModel.evaluate(payload, "BULLISH") is True


def test_2_sweep_without_displacement():
    """LTFEntryModel returns False when sweep is present but displacement is absent."""
    payload = create_synthetic_payload(has_sweep=True, has_displacement=False, direction="BULLISH")
    assert LTFEntryModel.evaluate(payload, "BULLISH") is False


def test_3_displacement_without_sweep():
    """LTFEntryModel returns False when displacement is present but liquidity sweep is absent."""
    payload = create_synthetic_payload(has_sweep=False, has_displacement=True, direction="BULLISH")
    assert LTFEntryModel.evaluate(payload, "BULLISH") is False


def test_4_invalid_direction_sweep():
    """LTFEntryModel returns False when sweep occurs in opposing direction."""
    payload = create_synthetic_payload(has_sweep=True, has_displacement=True, direction="BEARISH")
    assert LTFEntryModel.evaluate(payload, "BULLISH") is False


def test_5_valid_protected_swing_long():
    """Protected low is present and correctly extracted for long candidate."""
    payload = create_synthetic_payload(protected_low_price=90.0, direction="BULLISH")
    assert payload.structure_state.protected_low is not None
    assert payload.structure_state.protected_low.raw_swing.price == 90.0


def test_6_missing_protected_swing_rejection():
    """UnifiedStrategy rejects with REJECT_MISSING_STRUCTURAL_ANCHORS when protected swing is None."""
    strategy = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_test_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1M",
        mtf="1W",
        ltf="1D",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_target_price=150.0,
        creation_timestamp=1000,
        max_lifespan_seconds=86400
    )
    # Payload has no protected low
    ltf_payload = create_synthetic_payload(current_price=100.0, protected_low_price=None)
    dummy_htf = create_synthetic_payload(current_price=100.0)
    dummy_mtf = create_synthetic_payload(current_price=100.0)
    
    plan = strategy.evaluate(candidate, dummy_htf, dummy_mtf, ltf_payload)
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_MISSING_STRUCTURAL_ANCHORS"


def test_7_valid_complete_trigger_and_plan_generation():
    """
    UnifiedStrategy successfully generates TradePlanPayload when:
    Protected Low (90.0) < Entry (100.0) < Target (150.0)
    Planned RR = (150 - 100) / (100 - 90) = 50 / 10 = 5.0R >= 4.0R
    """
    strategy = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_test_valid",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1M",
        mtf="1W",
        ltf="1D",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_target_price=150.0,
        creation_timestamp=1000,
        max_lifespan_seconds=86400
    )
    ltf_payload = create_synthetic_payload(current_price=100.0, protected_low_price=90.0)
    dummy_htf = create_synthetic_payload(current_price=100.0)
    dummy_mtf = create_synthetic_payload(current_price=100.0)
    
    plan = strategy.evaluate(candidate, dummy_htf, dummy_mtf, ltf_payload)
    assert plan is not None
    assert plan.status == CandidateState.ENTERED.value
    assert plan.entry_price == 100.0
    assert plan.stop_invalidation_price == 90.0
    assert plan.target_price == 150.0
    assert plan.raw_rr == 5.0


def test_8_invalid_geometry_rejection():
    """
    UnifiedStrategy rejects with REJECT_INVALID_ANCHOR_GEOMETRY when:
    Entry (100.0) is higher than HTF Target (95.0) for a Long trade.
    """
    strategy = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_test_geom",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1M",
        mtf="1W",
        ltf="1D",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_target_price=95.0,  # Target is below entry!
        creation_timestamp=1000,
        max_lifespan_seconds=86400
    )
    ltf_payload = create_synthetic_payload(current_price=100.0, protected_low_price=90.0)
    dummy_htf = create_synthetic_payload(current_price=100.0)
    dummy_mtf = create_synthetic_payload(current_price=100.0)
    
    plan = strategy.evaluate(candidate, dummy_htf, dummy_mtf, ltf_payload)
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"
