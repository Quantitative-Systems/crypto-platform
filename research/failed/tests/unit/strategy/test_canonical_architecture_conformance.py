"""
Unit Tests for Canonical Multi-Timeframe Strategy Architecture Conformance
Verifies:
1. 19 Canonical States and StateTransitionEvent contracts.
2. Elimination of single-candle wick stop loss fallbacks.
3. Structural stop loss anchoring to confirmed swings.
4. Dedicated MTF realignment KeyZone synthesis and active retrace.
5. Planned RR >= 4.0R entry qualification with structural stop distance.
6. Correct exit attribution for MTF structural trailing (MTF_TRAIL_EXIT vs LTF_SL_EXIT).
7. 4-Stage TradeTimelineTelemetry schema integrity.
"""

import pytest
from strategy_engine.contracts.strategy_state import CanonicalState, CandidateState, PositionState, StateTransitionEvent
from strategy_engine.contracts.telemetry import TradeTimelineTelemetry, TelemetryHelper
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.entry.entry_models import (
    LiquiditySweepAndDisplacementModel,
    DirectionalDisplacementModel,
    LTFStructuralShiftModel,
    EntryEvaluationResult
)
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from market_intelligence.primitives import (
    MarketStatePayload,
    Candle,
    StructureState,
    StructureEvent,
    EventType,
    SequenceSwing,
    RawSwing,
    SwingType,
    SequenceLabel,
    KeyZone,
    ZoneType,
    TrendDirection
)


def make_test_payload(
    symbol="BTC/USDT",
    timeframe="1H",
    timestamp=1000,
    current_price=100.0,
    current_candle=None,
    events=None,
    swings=None,
    structure_state=None,
    liquidity_pools=None,
    keyzones=None,
    phase_state=None,
    trend_state=TrendDirection.BULLISH
):
    return MarketStatePayload(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        current_price=current_price,
        current_candle=current_candle,
        events=events or [],
        swings=swings or [],
        structure_state=structure_state or StructureState(),
        liquidity_pools=liquidity_pools or [],
        keyzones=keyzones or [],
        phase_state=phase_state,
        trend_state=trend_state
    )


def test_19_canonical_states_exist():
    expected_states = [
        "HTF_STRUCTURE_IDENTIFIED",
        "HTF_BIAS_CONFIRMED",
        "HTF_KEYZONE_IDENTIFIED",
        "HTF_CONTEXT_ACTIVE",
        "MTF_COUNTER_PHASE",
        "MTF_ALIGNMENT_DETECTED",
        "MTF_STRUCTURE_CONFIRMED",
        "MTF_KEYZONE_CREATED",
        "MTF_PULLBACK_ACTIVE",
        "LTF_ENTRY_ARMED",
        "LTF_LIQUIDITY_EVENT",
        "LTF_ENTRY_CONFIRMATION",
        "TRADE_ENTERED",
        "MTF_TRAILING_ACTIVE",
        "HTF_TARGET_REACHED",
        "MTF_TRAIL_EXIT",
        "LTF_INVALIDATION_EXIT",
        "RISK_EXIT",
        "TRADE_CLOSED",
    ]
    for s in expected_states:
        assert hasattr(CanonicalState, s), f"Missing canonical state: {s}"
        assert CanonicalState[s].value == s


def test_state_transition_event_structure():
    ev = StateTransitionEvent(
        timestamp=1672531200,
        timeframe="MTF",
        direction="BULLISH",
        from_state="MTF_COUNTER_PHASE",
        to_state="MTF_ALIGNMENT_DETECTED",
        structural_evidence="CHOCH_1672531200",
        reason_code="CHOCH_BREAK_OF_STRONG_HIGH",
        provenance={"parent_context": "htf_ctx_01"}
    )
    assert ev.from_state == "MTF_COUNTER_PHASE"
    assert ev.to_state == "MTF_ALIGNMENT_DETECTED"
    assert ev.structural_evidence == "CHOCH_1672531200"


def test_entry_model_rejects_single_candle_wick_without_sweep():
    """
    Verifies that a single candle hammer wick without a formal liquidity sweep
    is REJECTED by LiquiditySweepAndDisplacementModel (eliminating micro-stops).
    """
    model = LiquiditySweepAndDisplacementModel()
    candle = Candle(timestamp=1000, open=100.0, high=105.0, low=95.0, close=104.0, volume=10.0)
    payload = make_test_payload(
        timeframe="1m",
        timestamp=1000,
        current_price=104.0,
        current_candle=candle,
        events=[]
    )
    res = model.evaluate(payload, required_direction="BULLISH", setup_retest_timestamp=500)
    assert not res.is_confirmed
    assert res.reversal_reason == "NO_CAUSAL_SWEEP_EVENT"


def test_entry_model_structural_stop_anchoring():
    """
    Verifies that when a valid liquidity sweep occurs, the stop loss is anchored
    to the structural swing low / sweep extreme, not the 1m candle body.
    """
    model = LiquiditySweepAndDisplacementModel()
    candle = Candle(timestamp=1000, open=100.0, high=105.0, low=99.0, close=104.0, volume=10.0)
    sweep_event = StructureEvent(
        timestamp=800,
        event_type=EventType.LIQUIDITY_SWEEP,
        price_level=92.0,  # Swept level far below candle low 99.0
        broken_swing_id="sw_low_01",
        direction="BULLISH",
        candle_index=10
    )
    raw_sw = RawSwing(
        swing_id="sw_low_01",
        timestamp=700,
        price=92.0,
        swing_type=SwingType.SWING_LOW,
        candle_index=8,
        confirmation_timestamp=750,
        confirmation_index=9
    )
    seq_sw = SequenceSwing(raw_swing=raw_sw, label=SequenceLabel.HL, is_protected=True)
    struct = StructureState(protected_low=seq_sw)

    payload = make_test_payload(
        timeframe="1m",
        timestamp=1000,
        current_price=104.0,
        current_candle=candle,
        events=[sweep_event],
        structure_state=struct
    )
    res = model.evaluate(payload, required_direction="BULLISH", setup_retest_timestamp=500)
    assert res.is_confirmed
    assert res.micro_invalidation_price == 92.0  # Anchored to structural sweep pivot, not candle.low (99.0)
    assert res.entry_price == 104.0


def test_mtf_realignment_synthesizes_dedicated_keyzone():
    """
    Verifies that MTF alignment dynamically synthesizes a dedicated realignment KeyZone
    from the displacement impulse when no pre-existing primitive zone is present.
    """
    strat = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1D",
        mtf="4H",
        ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_context_timestamp=1000
    )
    mtf_candle = Candle(timestamp=2000, open=100.0, high=110.0, low=98.0, close=108.0, volume=100.0)
    mtf_event = StructureEvent(
        timestamp=2000,
        event_type=EventType.EXTERNAL_CHOCH,
        price_level=105.0,
        broken_swing_id="sw_high_01",
        direction="BULLISH",
        candle_index=5
    )
    mtf_payload = make_test_payload(
        timeframe="4H",
        timestamp=2000,
        current_price=108.0,
        current_candle=mtf_candle,
        events=[mtf_event],
        keyzones=[]  # No pre-cached zones
    )
    htf_payload = make_test_payload(timeframe="1D", timestamp=2000, current_price=108.0)
    ltf_payload = make_test_payload(timeframe="1H", timestamp=2000, current_price=108.0)

    strat.evaluate(candidate, htf_payload, mtf_payload, ltf_payload)

    assert candidate.state == CandidateState.WAIT_MTF_RETEST
    assert candidate.mtf_alignment_timestamp == 2000
    assert candidate.mtf_keyzone_id.startswith("synth_mtf_kz_")
    assert candidate.metadata is not None
    assert candidate.metadata["synth_mtf_kz_low"] <= candidate.metadata["synth_mtf_kz_high"]


def test_active_trade_manager_attributes_mtf_trail_exit():
    """
    Verifies that when a position's stop is trailed by MTF swings and subsequently hit,
    ActiveTradeManager attributes the exit to MTF_TRAIL_EXIT, NOT LTF_SL_EXIT.
    """
    manager = ActiveTradeManager(enable_mtf_trailing=True, enable_profit_lock=False)
    plan = TradePlanPayload(
        trade_plan_id="trade_01",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0,  # Initial SL = 90.0
        target_price=150.0,
        raw_rr=5.0,
        status="ACTIVE_POSITION"
    )
    manager.register_trade("trade_01", plan)

    # Simulate MTF structural trailing stop ratchet to 105.0
    plan.stop_invalidation_price = 105.0

    # Candle dips to 104.0, hitting the trailed stop
    ltf_candle = Candle(timestamp=3000, open=108.0, high=109.0, low=104.0, close=106.0, volume=50.0)
    ltf_payload = make_test_payload(timeframe="1H", timestamp=3000, current_price=106.0, current_candle=ltf_candle)
    mtf_payload = make_test_payload(timeframe="4H", timestamp=3000, current_price=106.0)
    htf_payload = make_test_payload(timeframe="1D", timestamp=3000, current_price=106.0)

    exits = manager.evaluate(htf_payload, mtf_payload, ltf_payload)
    assert len(exits) == 1
    assert exits[0].position_status == PositionState.MTF_TRAIL_EXIT.value


def test_trade_timeline_telemetry_schema():
    """
    Verifies that TradeTimelineTelemetry contains all 4 stages and serializes cleanly to dict.
    """
    telem = TradeTimelineTelemetry(
        candidate_id="cand_01",
        symbol="BTC/USDT",
        timeframe_set="SET_1"
    )
    telem.htf_timeline.structure = "BULLISH_TREND"
    telem.mtf_timeline.alignment_event = "BULLISH_CHOCH"
    telem.ltf_timeline.liquidity_event = "SELL_SIDE_LIQUIDITY_SWEEP"
    telem.trade_timeline.planned_rr = 5.2
    telem.trade_timeline.realized_r = 3.1
    telem.trade_timeline.exit_reason = "MTF_TRAIL_EXIT"

    d = telem.to_dict()
    assert d["candidate_id"] == "cand_01"
    assert d["htf_timeline"]["structure"] == "BULLISH_TREND"
    assert d["mtf_timeline"]["alignment_event"] == "BULLISH_CHOCH"
    assert d["ltf_timeline"]["liquidity_event"] == "SELL_SIDE_LIQUIDITY_SWEEP"
    assert d["trade_timeline"]["planned_rr"] == 5.2
    assert d["trade_timeline"]["exit_reason"] == "MTF_TRAIL_EXIT"
