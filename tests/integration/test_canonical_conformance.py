"""
Canonical Strategy Synthetic Conformance Suite
Verifies the 8 core canonical trading hypothesis rules across P01, P02, P03, and P04.
"""

import pytest
from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, RawSwing, SequenceSwing, SequenceLabel, SwingScope,
    MarketEvent, StructureState, SwingType, SwingStatus, EventType
)
from market_intelligence.structure_builder_engine import StructureEvent
from market_intelligence.keyzone_engine import KeyZone, KeyZoneType, ZoneScope, ZoneStatus
from market_intelligence.phase_engine import MarketPhase
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.pullback_riding import PullbackRidingHypothesis
from strategy_engine.hypotheses.continuation_riding import ContinuationRidingHypothesis
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload
from research.replayer.timeframe_aligner import TimeframeAligner


def make_swing(price: float, swing_type: SwingType = SwingType.SWING_LOW) -> SequenceSwing:
    raw = RawSwing(
        swing_id="sw1",
        timestamp=1000,
        price=price,
        swing_type=swing_type,
        candle_index=1,
        confirmation_timestamp=1000,
        confirmation_index=1,
        scope=SwingScope.EXTERNAL
    )
    return SequenceSwing(raw_swing=raw, label=SequenceLabel.HL)


def make_dummy_payload(symbol="BTCUSD", timeframe="1H", timestamp=1000, trend=TrendDirection.BULLISH, phase=MarketPhase.EXPANSION, current_price=100.0):
    return MarketStatePayload(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        current_price=current_price,
        current_candle=Candle(timestamp=timestamp, open=current_price, high=current_price+1, low=current_price-1, close=current_price, volume=100),
        events=[],
        swings=[],
        structure_state=StructureState(
            external_trend=trend,
            internal_trend=trend,
            protected_low=make_swing(90.0, SwingType.SWING_LOW),
            weak_high=make_swing(150.0, SwingType.SWING_HIGH)
        ),
        liquidity_pools=[],
        keyzones=[],
        phase_state=phase,
        trend_state=trend,
        valuation_state="EQUILIBRIUM",
        scorecard={"validation_score": 100, "reason_codes": ["DISPLACEMENT_CONFIRMED"], "validation_status": "VALID"},
        metadata={}
    )


def test_scenario_1_htf_bullish_mtf_bearish_no_entry():
    """Scenario 1: HTF = Bullish, MTF = Bearish (Pullback), LTF = Bullish -> NO ENTRY (MTF not realigned)."""
    htf = make_dummy_payload(timeframe="1D", trend=TrendDirection.BULLISH, phase=MarketPhase.EXPANSION)
    mtf = make_dummy_payload(timeframe="4H", trend=TrendDirection.BEARISH, phase=MarketPhase.PULLBACK)
    ltf = make_dummy_payload(timeframe="1H", trend=TrendDirection.BULLISH)
    
    candidate = CandidateSetup(
        candidate_id="cand_1",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = PullbackRidingHypothesis()
    # MTF has no bullish CHOCH event yet
    plan = hyp.evaluate(candidate, htf, mtf, ltf)
    assert plan is None
    assert candidate.state == CandidateState.WAIT_MTF_ALIGNMENT


def test_scenario_2_htf_bullish_mtf_bullish_ltf_bearish_no_entry():
    """Scenario 2: HTF = Bullish, MTF = Bullish, LTF = Bearish (No trigger) -> NO ENTRY."""
    ltf = make_dummy_payload(timeframe="1H", trend=TrendDirection.BEARISH)
    # No liquidity sweep in LTF
    assert LTFEntryModel.evaluate(ltf, "BULLISH") is False


def test_scenario_3_rr_below_4_rejected():
    """Scenario 3: HTF/MTF/LTF Bullish, but RR = 3.0 (< 4.0) -> Rejection."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(130.0, SwingType.SWING_HIGH) # Target = 130 (Pullback Long uses protected_high)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0) # Entry = 100
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW) # SL = 90
    # Risk = 10, Reward = 30 -> RR = 3.0 < 4.0
    
    candidate = CandidateSetup(
        candidate_id="cand_3",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = PullbackRidingHypothesis()
    plan = hyp.evaluate(candidate, htf, make_dummy_payload(timeframe="4H"), ltf)
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_RR_BELOW_4R"


def test_scenario_4_valid_entry_and_risk_sizing():
    """Scenario 4: RR = 5.0 (>= 4.0), Risk <= 1.0% -> ENTRY accepted and properly sized."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(150.0, SwingType.SWING_HIGH) # Target = 150 (Pullback Long uses protected_high)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0) # Entry = 100
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW) # SL = 90
    # Risk = 10, Reward = 50 -> RR = 5.0 >= 4.0
    
    candidate = CandidateSetup(
        candidate_id="cand_4",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = PullbackRidingHypothesis()
    plan = hyp.evaluate(candidate, htf, make_dummy_payload(timeframe="4H"), ltf)
    assert plan is not None
    assert plan.status == CandidateState.ENTERED.value
    assert plan.raw_rr == 5.0
    
    # Process through P03 Risk Firewall
    account = AccountState(current_equity=10000.0, peak_equity=10000.0, daily_pnl=0.0, weekly_pnl=0.0, open_position_count=0)
    risk_result = RiskCoordinator.evaluate(plan, account)
    assert isinstance(risk_result, RiskApprovedPlan)
    assert risk_result.dollar_risk == 100.0 # Exactly 1.0% of $10,000
    assert risk_result.position_units == 10.0 # $100 / $10 stop distance


def test_target_distinction_pullback_long_targets_protected_high():
    """Target Rule 1: Pullback Riding LONG targets HTF protected_high (Strong High)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(200.0, SwingType.SWING_HIGH)
    htf.structure_state.weak_high = make_swing(120.0, SwingType.SWING_HIGH)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(80.0, SwingType.SWING_LOW)
    
    candidate = CandidateSetup(
        candidate_id="c_pb_l", hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = PullbackRidingHypothesis().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 200.0  # Uses protected_high, NOT weak_high (120.0)


def test_target_distinction_pullback_short_targets_protected_low():
    """Target Rule 2: Pullback Riding SHORT targets HTF protected_low (Strong Low)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_low = make_swing(50.0, SwingType.SWING_LOW)
    htf.structure_state.weak_low = make_swing(80.0, SwingType.SWING_LOW)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_high = make_swing(110.0, SwingType.SWING_HIGH)
    
    candidate = CandidateSetup(
        candidate_id="c_pb_s", hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan = PullbackRidingHypothesis().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 50.0  # Uses protected_low, NOT weak_low (80.0)


def test_target_distinction_continuation_long_targets_weak_high():
    """Target Rule 3: Continuation Riding LONG targets HTF weak_high (Weak High)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(200.0, SwingType.SWING_HIGH)
    htf.structure_state.weak_high = make_swing(160.0, SwingType.SWING_HIGH)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(88.0, SwingType.SWING_LOW)
    
    candidate = CandidateSetup(
        candidate_id="c_cont_l", hypothesis_id="HYP_B_CONTINUATION_RIDING",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = ContinuationRidingHypothesis().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 160.0  # Uses weak_high, NOT protected_high (200.0)


def test_target_distinction_continuation_short_targets_weak_low():
    """Target Rule 4: Continuation Riding SHORT targets HTF weak_low (Weak Low)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_low = make_swing(40.0, SwingType.SWING_LOW)
    htf.structure_state.weak_low = make_swing(70.0, SwingType.SWING_LOW)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_high = make_swing(105.0, SwingType.SWING_HIGH)
    
    candidate = CandidateSetup(
        candidate_id="c_cont_s", hypothesis_id="HYP_B_CONTINUATION_RIDING",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan = ContinuationRidingHypothesis().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 70.0  # Uses weak_low, NOT protected_low (40.0)


def test_scenario_5_mtf_trailing_protection_invariance():
    """Scenario 5: MTF structural trailing ratchets upward on new MTF swing, and never widens."""
    atm = ActiveTradeManager()
    plan = TradePlanPayload(
        trade_plan_id="trade_5",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0,
        target_price=150.0,
        raw_rr=5.0,
        status="ENTERED",
        source_timeframes={"HTF": "1D", "MTF": "4H", "LTF": "1H"}
    )
    atm.register_trade("trade_5", plan)
    
    # 1. New MTF structure forms higher low at 95.0
    mtf_higher = make_dummy_payload(timeframe="4H", current_price=110.0)
    mtf_higher.structure_state.protected_low = make_swing(95.0, SwingType.SWING_LOW)
    atm.evaluate(make_dummy_payload(timeframe="1D", current_price=110.0), mtf_higher, make_dummy_payload(timeframe="1H", current_price=110.0))
    
    # Stop ratcheted from 90.0 to 95.0
    assert plan.stop_invalidation_price == 95.0
    
    # 2. MTF temporary noise / lower swing reported at 88.0 -> Stop must NOT widen
    mtf_lower = make_dummy_payload(timeframe="4H", current_price=105.0)
    mtf_lower.structure_state.protected_low = make_swing(88.0, SwingType.SWING_LOW)
    atm.evaluate(make_dummy_payload(timeframe="1D", current_price=105.0), mtf_lower, make_dummy_payload(timeframe="1H", current_price=105.0))
    
    # Stop remains at 95.0 (invariance maintained)
    assert plan.stop_invalidation_price == 95.0


def test_scenario_6_pullback_riding_lifecycle():
    """Scenario 6: Full Pullback Riding candidate lifecycle progression."""
    hyp = PullbackRidingHypothesis()
    candidate = CandidateSetup(
        candidate_id="cand_6",
        hypothesis_id="HYP_A_PULLBACK_RIDING",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    # 1. MTF prints Bullish CHOCH
    mtf_choch = make_dummy_payload(timeframe="4H")
    mtf_choch.events = [
        MarketEvent(
            timestamp=1000,
            timeframe="4H",
            symbol="BTCUSD",
            event_type=EventType.INTERNAL_CHOCH,
            price_level=100.0,
            metadata={"direction": "BULLISH", "broken_swing_id": "sw_brk"}
        )
    ]
    hyp.evaluate(candidate, make_dummy_payload("1D"), mtf_choch, make_dummy_payload("1H"))
    assert candidate.state == CandidateState.WAIT_MTF_RETEST
    
    # 2. MTF KeyZone mitigated (Retest)
    mtf_retest = make_dummy_payload(timeframe="4H")
    mtf_retest.keyzones = [
        KeyZone(
            zone_id="kz_1",
            zone_type=KeyZoneType.BULLISH_OB,
            scope=ZoneScope.INTERNAL,
            price_level=95.0,
            high_boundary=96.0,
            low_boundary=94.0,
            creation_timestamp=1000,
            creation_candle_index=1,
            status=ZoneStatus.MITIGATED
        )
    ]
    hyp.evaluate(candidate, make_dummy_payload("1D"), mtf_retest, make_dummy_payload("1H"))
    assert candidate.state == CandidateState.WAIT_LTF_TRIGGER
    
    # 3. LTF Trigger (Sweep + Displacement)
    ltf_trigger = make_dummy_payload(timeframe="1H")
    ltf_trigger.events = [
        MarketEvent(
            timestamp=1100,
            timeframe="1H",
            symbol="BTCUSD",
            event_type=EventType.LIQUIDITY_SWEEP,
            price_level=92.0,
            metadata={"direction": "BULLISH"}
        )
    ]
    hyp.evaluate(candidate, make_dummy_payload("1D"), mtf_retest, ltf_trigger)
    assert candidate.state == CandidateState.RISK_GATE


def test_scenario_7_continuation_riding_lifecycle():
    """Scenario 7: Full Continuation Riding candidate lifecycle progression (BOS alignment)."""
    hyp = ContinuationRidingHypothesis()
    candidate = CandidateSetup(
        candidate_id="cand_7",
        hypothesis_id="HYP_B_CONTINUATION_RIDING",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    # 1. MTF prints Bullish BOS
    mtf_bos = make_dummy_payload(timeframe="4H")
    mtf_bos.events = [
        MarketEvent(
            timestamp=1000,
            timeframe="4H",
            symbol="BTCUSD",
            event_type=EventType.INTERNAL_BOS,
            price_level=100.0,
            metadata={"direction": "BULLISH", "broken_swing_id": "sw_brk"}
        )
    ]
    hyp.evaluate(candidate, make_dummy_payload("1D"), mtf_bos, make_dummy_payload("1H"))
    assert candidate.state == CandidateState.WAIT_MTF_RETEST


def test_scenario_8_zero_lookahead_filtering():
    """Scenario 8: Future / unclosed higher timeframe candles are mathematically hidden."""
    candles_4h = [
        Candle(timestamp=0, open=100, high=105, low=99, close=102, volume=1000),      # Closes at 14400000 ms
        Candle(timestamp=14400000, open=102, high=110, low=101, close=108, volume=1000), # Closes at 28800000 ms
        Candle(timestamp=28800000, open=108, high=120, low=107, close=115, volume=1000), # Closes at 43200000 ms
    ]
    
    # At decision timestamp = 20000000 ms (inside Bar 2, before it closes at 28800000 ms)
    visible = TimeframeAligner.filter_visible_candles(candles_4h, decision_timestamp=20000000, timeframe="4H")
    
    # Only Bar 1 has closed! Bar 2 and Bar 3 MUST be hidden
    assert len(visible) == 1
    assert visible[0].timestamp == 0
