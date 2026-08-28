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
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload
from research.replayer.timeframe_aligner import TimeframeAligner

# Monkey patch for tests bypassing StrategyCoordinator
original_eval = UnifiedStrategy.evaluate
def mock_eval(self, candidate, htf, mtf, ltf):
    if candidate.htf_target_price is None:
        if candidate.directional_permission.value == 'PERMIT_LONG' and htf.structure_state and htf.structure_state.weak_high:
            candidate.htf_target_price = htf.structure_state.weak_high.raw_swing.price
        elif candidate.directional_permission.value == 'PERMIT_SHORT' and htf.structure_state and htf.structure_state.weak_low:
            candidate.htf_target_price = htf.structure_state.weak_low.raw_swing.price
    return original_eval(self, candidate, htf, mtf, ltf)
UnifiedStrategy.evaluate = mock_eval


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
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = UnifiedStrategy()
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
    htf.structure_state.weak_high = make_swing(130.0, SwingType.SWING_HIGH) # Target = 130
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0) # Entry = 100
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW) # SL = 90
    # Risk = 10, Reward = 30 -> RR = 3.0 < 4.0
    
    candidate = CandidateSetup(
        candidate_id="cand_3",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = UnifiedStrategy()
    plan = hyp.evaluate(candidate, htf, make_dummy_payload(timeframe="4H"), ltf)
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_RR_BELOW_4R"


def test_scenario_4_valid_entry_and_risk_sizing():
    """Scenario 4: RR = 5.0 (>= 4.0), Risk <= 1.0% -> ENTRY accepted and properly sized."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(150.0, SwingType.SWING_HIGH) # Target = 150
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0) # Entry = 100
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW) # SL = 90
    # Risk = 10, Reward = 50 -> RR = 5.0 >= 4.0
    
    candidate = CandidateSetup(
        candidate_id="cand_4",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG
    )
    
    hyp = UnifiedStrategy()
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


def test_target_canonical_pullback_long_targets_weak_high():
    """Target Rule 1: Pullback Riding LONG targets HTF weak_high (Expansion Target / Weak High)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(200.0, SwingType.SWING_HIGH)
    htf.structure_state.weak_high = make_swing(140.0, SwingType.SWING_HIGH)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(80.0, SwingType.SWING_LOW)
    
    candidate = CandidateSetup(
        candidate_id="c_pb_l", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = UnifiedStrategy().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 140.0  # Uses weak_high, NOT protected_high (200.0)


def test_target_canonical_pullback_short_targets_weak_low():
    """Target Rule 2: Pullback Riding SHORT targets HTF weak_low (Expansion Target / Weak Low)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_low = make_swing(50.0, SwingType.SWING_LOW)
    htf.structure_state.weak_low = make_swing(70.0, SwingType.SWING_LOW)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_high = make_swing(105.0, SwingType.SWING_HIGH)
    
    candidate = CandidateSetup(
        candidate_id="c_pb_s", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan = UnifiedStrategy().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 70.0  # Uses weak_low, NOT protected_low (50.0)


def test_target_distinction_continuation_long_targets_weak_high():
    """Target Rule 3: Continuation Riding LONG targets HTF weak_high (Weak High)."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.protected_high = make_swing(200.0, SwingType.SWING_HIGH)
    htf.structure_state.weak_high = make_swing(160.0, SwingType.SWING_HIGH)
    
    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(88.0, SwingType.SWING_LOW)
    
    candidate = CandidateSetup(
        candidate_id="c_cont_l", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = UnifiedStrategy().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
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
        candidate_id="c_cont_s", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan = UnifiedStrategy().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
    assert plan is not None
    assert plan.target_price == 70.0  # Uses weak_low, NOT protected_low (40.0)


# ============================================================================
# G4.3 REGRESSION COVERAGE SUITE (STEP 4)
# ============================================================================

def test_regression_bullish_anchor_mapping():
    """Regression 1: Bullish anchor mapping -> SL = LTF protected_low, TP = HTF weak_high."""
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(150.0, SwingType.SWING_HIGH)
    htf.structure_state.protected_high = make_swing(180.0, SwingType.SWING_HIGH)

    ltf = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW)
    ltf.structure_state.weak_low = make_swing(85.0, SwingType.SWING_LOW)

    for HypClass, hyp_id in [(UnifiedStrategy, "UNIFIED_STRATEGY")]:
        candidate = CandidateSetup(
            candidate_id=f"c_reg_bull_{hyp_id}", hypothesis_id=hyp_id,
            symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
            state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
        )
        plan = HypClass().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
        assert plan is not None
        assert plan.stop_invalidation_price == 90.0  # LTF protected_low
        assert plan.target_price == 150.0           # HTF weak_high
        assert plan.status == CandidateState.ENTERED.value


def test_regression_bearish_anchor_mapping():
    """Regression 2: Bearish anchor mapping -> SL = LTF protected_high, TP = HTF weak_low."""
    htf = make_dummy_payload(timeframe="1D", trend=TrendDirection.BEARISH)
    htf.structure_state.weak_low = make_swing(50.0, SwingType.SWING_LOW)
    htf.structure_state.protected_low = make_swing(40.0, SwingType.SWING_LOW)

    ltf = make_dummy_payload(timeframe="1H", trend=TrendDirection.BEARISH, current_price=100.0)
    ltf.structure_state.protected_high = make_swing(110.0, SwingType.SWING_HIGH)
    ltf.structure_state.weak_high = make_swing(115.0, SwingType.SWING_HIGH)

    for HypClass, hyp_id in [(UnifiedStrategy, "UNIFIED_STRATEGY")]:
        candidate = CandidateSetup(
            candidate_id=f"c_reg_bear_{hyp_id}", hypothesis_id=hyp_id,
            symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
            state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
        )
        plan = HypClass().evaluate(candidate, htf, make_dummy_payload("4H"), ltf)
        assert plan is not None
        assert plan.stop_invalidation_price == 110.0  # LTF protected_high
        assert plan.target_price == 50.0             # HTF weak_low
        assert plan.status == CandidateState.ENTERED.value


def test_regression_invalid_long_geometry():
    """Regression 3: Invalid Long geometry (not SL < Entry < TP) -> REJECT_INVALID_ANCHOR_GEOMETRY."""
    # Case A: Entry below SL (Entry=85, SL=90, TP=150)
    htf = make_dummy_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(150.0, SwingType.SWING_HIGH)

    ltf_below_sl = make_dummy_payload(timeframe="1H", current_price=85.0)
    ltf_below_sl.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW)

    candidate_a = CandidateSetup(
        candidate_id="c_inv_l_a", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan_a = UnifiedStrategy().evaluate(candidate_a, htf, make_dummy_payload("4H"), ltf_below_sl)
    assert plan_a is not None
    assert plan_a.status == CandidateState.REJECTED.value
    assert plan_a.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"
    assert plan_a.raw_rr == 0.0

    # Case B: Entry above TP (Entry=160, SL=90, TP=150)
    ltf_above_tp = make_dummy_payload(timeframe="1H", current_price=160.0)
    ltf_above_tp.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW)

    candidate_b = CandidateSetup(
        candidate_id="c_inv_l_b", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan_b = UnifiedStrategy().evaluate(candidate_b, htf, make_dummy_payload("4H"), ltf_above_tp)
    assert plan_b is not None
    assert plan_b.status == CandidateState.REJECTED.value
    assert plan_b.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"


def test_regression_invalid_short_geometry():
    """Regression 4: Invalid Short geometry (not TP < Entry < SL) -> REJECT_INVALID_ANCHOR_GEOMETRY."""
    # Case A: Entry above SL (Entry=115, SL=110, TP=50)
    htf = make_dummy_payload(timeframe="1D", trend=TrendDirection.BEARISH)
    htf.structure_state.weak_low = make_swing(50.0, SwingType.SWING_LOW)

    ltf_above_sl = make_dummy_payload(timeframe="1H", trend=TrendDirection.BEARISH, current_price=115.0)
    ltf_above_sl.structure_state.protected_high = make_swing(110.0, SwingType.SWING_HIGH)

    candidate_a = CandidateSetup(
        candidate_id="c_inv_s_a", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan_a = UnifiedStrategy().evaluate(candidate_a, htf, make_dummy_payload("4H"), ltf_above_sl)
    assert plan_a is not None
    assert plan_a.status == CandidateState.REJECTED.value
    assert plan_a.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"
    assert plan_a.raw_rr == 0.0

    # Case B: Entry below TP (Entry=45, SL=110, TP=50)
    ltf_below_tp = make_dummy_payload(timeframe="1H", trend=TrendDirection.BEARISH, current_price=45.0)
    ltf_below_tp.structure_state.protected_high = make_swing(110.0, SwingType.SWING_HIGH)

    candidate_b = CandidateSetup(
        candidate_id="c_inv_s_b", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan_b = UnifiedStrategy().evaluate(candidate_b, htf, make_dummy_payload("4H"), ltf_below_tp)
    assert plan_b is not None
    assert plan_b.status == CandidateState.REJECTED.value
    assert plan_b.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"


def test_regression_rr_calculation_after_geometry_validation():
    """Regression 5: Planned RR calculated only after geometry passes, enforcing >= 4.0 threshold."""
    htf = make_dummy_payload(timeframe="1D")
    
    # 5.1 Valid geometry, RR = 2.0 (Reward=20, Risk=10) -> Rejected with REJECT_RR_BELOW_4R
    htf.structure_state.weak_high = make_swing(120.0, SwingType.SWING_HIGH)
    ltf_low_rr = make_dummy_payload(timeframe="1H", current_price=100.0)
    ltf_low_rr.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW)

    c_low_rr = CandidateSetup(
        candidate_id="c_low_rr", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan_low_rr = UnifiedStrategy().evaluate(c_low_rr, htf, make_dummy_payload("4H"), ltf_low_rr)
    assert plan_low_rr is not None
    assert plan_low_rr.status == CandidateState.REJECTED.value
    assert plan_low_rr.rejection_reason == "REJECT_RR_BELOW_4R"
    assert plan_low_rr.raw_rr == 2.0

    # 5.2 Valid geometry, RR = 4.5 (Reward=45, Risk=10) -> ENTERED with exact raw_rr
    htf.structure_state.weak_high = make_swing(145.0, SwingType.SWING_HIGH)
    c_valid_rr = CandidateSetup(
        candidate_id="c_valid_rr", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan_valid_rr = UnifiedStrategy().evaluate(c_valid_rr, htf, make_dummy_payload("4H"), ltf_low_rr)
    assert plan_valid_rr is not None
    assert plan_valid_rr.status == CandidateState.ENTERED.value
    assert plan_valid_rr.raw_rr == 4.5
    assert plan_valid_rr.stop_invalidation_price == 90.0
    assert plan_valid_rr.target_price == 145.0


def test_scenario_5_mtf_trailing_protection_invariance():
    """Scenario 5: MTF structural trailing ratchets upward on new MTF swing, and never widens."""
    atm = ActiveTradeManager()
    plan = TradePlanPayload(
        trade_plan_id="trade_5",
        hypothesis_id="UNIFIED_STRATEGY",
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
    hyp = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_6",
        hypothesis_id="UNIFIED_STRATEGY",
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
    hyp = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_7",
        hypothesis_id="UNIFIED_STRATEGY",
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
        Candle(timestamp=1_000_000_000_000, open=100, high=105, low=99, close=102, volume=1000),      # Closes at 14400000 ms
        Candle(timestamp=1_000_014_400_000, open=102, high=110, low=101, close=108, volume=1000), # Closes at 28800000 ms
        Candle(timestamp=1_000_028_800_000, open=108, high=120, low=107, close=115, volume=1000), # Closes at 43200000 ms
    ]
    
    # At decision timestamp = 20000000 ms (inside Bar 2, before it closes at 28800000 ms)
    visible = TimeframeAligner.filter_visible_candles(candles_4h, decision_timestamp=1_000_020_000_000, timeframe="4H")
    
    # Only Bar 1 has closed! Bar 2 and Bar 3 MUST be hidden
    assert len(visible) == 1
    assert visible[0].timestamp == 1_000_000_000_000


def test_scenario_9_stale_mtf_keyzone_rejected():
    """Scenario 9: Stale historical MTF KeyZones created before MTF alignment are rejected."""
    hyp = UnifiedStrategy()
    candidate = CandidateSetup(
        candidate_id="cand_9",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_RETEST,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        mtf_alignment_timestamp=2000, metadata={"context": "PULLBACK"}
    )
    
    # MTF payload contains a stale keyzone created at T=1000 (< 2000)
    mtf_stale = make_dummy_payload(timeframe="4H", timestamp=2100)
    mtf_stale.keyzones = [
        KeyZone(
            zone_id="stale_kz",
            zone_type=KeyZoneType.BULLISH_OB,
            scope=ZoneScope.INTERNAL,
            price_level=95.0,
            high_boundary=96.0,
            low_boundary=94.0,
            creation_timestamp=1000,  # STALE: Created before alignment
            creation_candle_index=1,
            status=ZoneStatus.MITIGATED
        )
    ]
    
    hyp.evaluate(candidate, make_dummy_payload("1D"), mtf_stale, make_dummy_payload("1H"))
    # Candidate MUST NOT transition to WAIT_LTF_TRIGGER because keyzone is stale
    assert candidate.state == CandidateState.WAIT_MTF_RETEST
    assert candidate.mtf_keyzone_id is None


def test_scenario_10_intrabar_collision_adverse_precedence():
    """Scenario 10: When both SL and TP are touched in the same bar, SL takes precedence (adverse-first)."""
    from research.simulation.execution_simulator import ExecutionSimulator
    from research.simulation.trade_ledger import TradeLedger, SimulatedTrade

    sim = ExecutionSimulator()
    ledger = TradeLedger()
    trade = SimulatedTrade(
        trade_id="t_collision",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        timeframe_set="SET_3",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        fill_entry_price=100.0,
        initial_stop_price=90.0,
        current_stop_price=90.0,
        target_price=150.0,
        position_units=1.0,
        dollar_risk=10.0,
        status="ACTIVE"
    )
    ledger.trades["t_collision"] = trade

    # Ambiguous candle: Low touches SL (85 <= 90), High touches TP (160 >= 150)
    ambiguous_bar = Candle(timestamp=2000, open=100.0, high=160.0, low=85.0, close=110.0, volume=100.0)
    closed = sim.process_candle(ambiguous_bar, ledger)

    assert len(closed) == 1
    assert closed[0].status == "CLOSED"
    assert closed[0].exit_reason == "INITIAL_LTF_SL"  # Must exit via SL, NOT TP

