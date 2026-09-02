"""
Unit Tests for Canonical Strategy Ontology & Invariants
Validates:
1. Single executable strategy (UnifiedStrategy)
2. Contextual attribution (PULLBACK vs CONTINUATION)
3. 5 Canonical Timeframe Sets (SET_1 to SET_5)
4. Strict Directional Geometry (Long & Short)
5. Minimum Planned RR Floor (RR >= 4.0R)
6. Maximum Account Risk Ceiling (Risk <= 1.0%)
7. Monotonic MTF Structural Trailing Protection
"""

import pytest
from market_intelligence.primitives import (
    MarketStatePayload, Candle, TrendDirection, MarketPhase,
    StructureState, SequenceSwing, RawSwing, SwingType,
    SequenceLabel, StructuralRole, KeyZone, StructureEvent
)
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup, CandidateTracker
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from research.replayer.timeframe_aligner import TimeframeAligner, CANONICAL_TIMEFRAME_SETS
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator


def make_dummy_candle(ts: int = 1000, p: float = 100.0) -> Candle:
    return Candle(timestamp=ts, open=p, high=p + 1.0, low=p - 1.0, close=p, volume=100.0)


def make_dummy_sequence_swing(ts: int, price: float, swing_type: SwingType, role: StructuralRole) -> SequenceSwing:
    raw = RawSwing(
        swing_id=f"sw_{ts}",
        timestamp=ts,
        price=price,
        swing_type=swing_type,
        candle_index=1,
        confirmation_timestamp=ts,
        confirmation_index=1
    )
    label = SequenceLabel.HL if swing_type == SwingType.SWING_LOW else SequenceLabel.HH
    return SequenceSwing(raw_swing=raw, label=label, role=role)


def make_dummy_payload(
    timeframe: str = "1D",
    price: float = 100.0,
    trend: TrendDirection = TrendDirection.BULLISH,
    phase: MarketPhase = MarketPhase.PULLBACK
) -> MarketStatePayload:
    return MarketStatePayload(
        symbol="BTC/USDT",
        timeframe=timeframe,
        timestamp=1000,
        current_price=price,
        current_candle=make_dummy_candle(1000, price),
        trend_state=trend,
        phase_state=phase,
        structure_state=StructureState(
            external_trend=trend,
            internal_trend=trend,
            protected_low=make_dummy_sequence_swing(500, 90.0, SwingType.SWING_LOW, StructuralRole.PROTECTED_LOW),
            weak_high=make_dummy_sequence_swing(800, 150.0, SwingType.SWING_HIGH, StructuralRole.WEAK_HIGH)
        ),
        swings=[],
        liquidity_pools=[],
        keyzones=[],
        events=[]
    )


def test_timeframe_matrix_5_sets():
    """Validates that all 5 canonical timeframe sets are registered with correct scales."""
    assert len(CANONICAL_TIMEFRAME_SETS) == 5
    assert "SET_1" in CANONICAL_TIMEFRAME_SETS
    assert "SET_2" in CANONICAL_TIMEFRAME_SETS
    assert "SET_3" in CANONICAL_TIMEFRAME_SETS
    assert "SET_4" in CANONICAL_TIMEFRAME_SETS
    assert "SET_5" in CANONICAL_TIMEFRAME_SETS

    s1 = TimeframeAligner.get_set("SET_1")
    assert s1.htf == "1M" and s1.mtf == "1W" and s1.ltf == "1D"

    s5 = TimeframeAligner.get_set("SET_5")
    assert s5.htf == "15M" and s5.mtf == "5M" and s5.ltf in ["1m", "1M"]


def test_single_executable_strategy_ontology():
    """Validates that only one unified executable strategy evaluates setups."""
    coord = StrategyCoordinator()
    assert len(coord.hypotheses) == 1
    assert "UNIFIED_STRATEGY" in coord.hypotheses
    strategy = coord.hypotheses["UNIFIED_STRATEGY"]
    assert isinstance(strategy, UnifiedStrategy)


def test_contextual_attribution_pullback_and_continuation():
    """Validates that PULLBACK and CONTINUATION are tracked as HTF contextual metadata."""
    cand_pullback = CandidateSetup(
        candidate_id="cand_pb_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_phase="MarketPhase.PULLBACK",
        htf_context="PULLBACK"
    )
    prov_pb = cand_pullback.to_provenance_dict()
    assert prov_pb["htf_context"] == "PULLBACK"

    cand_cont = CandidateSetup(
        candidate_id="cand_cont_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTC/USDT",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_phase="MarketPhase.CONTINUATION",
        htf_context="CONTINUATION"
    )
    prov_cont = cand_cont.to_provenance_dict()
    assert prov_cont["htf_context"] == "CONTINUATION"


def test_directional_geometry_long_and_short():
    """Validates strict mathematical directional geometry: SL < Entry < TP (Long) and TP < Entry < SL (Short)."""
    hyp = UnifiedStrategy()
    
    # 1. Invalid Long Geometry (SL >= Entry)
    cand_long = CandidateSetup(
        candidate_id="c_long_inv", hypothesis_id="UNIFIED_STRATEGY", symbol="BTC/USDT",
        htf="1D", mtf="4H", ltf="1H", state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_target_price=150.0
    )
    ltf_long_inv = make_dummy_payload("1H", price=100.0)
    ltf_long_inv.structure_state.protected_low = make_dummy_sequence_swing(900, 105.0, SwingType.SWING_LOW, StructuralRole.PROTECTED_LOW) # SL (105) > Entry (100) -> Invalid!
    res = hyp.evaluate(cand_long, make_dummy_payload("1D"), make_dummy_payload("4H"), ltf_long_inv)
    assert res is not None and res.status == CandidateState.REJECTED.value
    assert "REJECT_INVALID_ANCHOR_GEOMETRY" in res.rejection_reason

    # 2. Invalid Short Geometry (Target >= Entry)
    cand_short = CandidateSetup(
        candidate_id="c_short_inv", hypothesis_id="UNIFIED_STRATEGY", symbol="BTC/USDT",
        htf="1D", mtf="4H", ltf="1H", state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_SHORT,
        htf_target_price=120.0 # Target (120) > Entry (100) for short -> Invalid!
    )
    ltf_short_inv = make_dummy_payload("1H", price=100.0, trend=TrendDirection.BEARISH)
    ltf_short_inv.structure_state.protected_high = make_dummy_sequence_swing(900, 110.0, SwingType.SWING_HIGH, StructuralRole.PROTECTED_HIGH)
    res_short = hyp.evaluate(cand_short, make_dummy_payload("1D"), make_dummy_payload("4H"), ltf_short_inv)
    assert res_short is not None and res_short.status == CandidateState.REJECTED.value
    assert "REJECT_INVALID_ANCHOR_GEOMETRY" in res_short.rejection_reason


def test_min_planned_rr_floor_4r():
    """Validates that planned RR < 4.0R is strictly rejected."""
    hyp = UnifiedStrategy()
    cand = CandidateSetup(
        candidate_id="c_rr_fail", hypothesis_id="UNIFIED_STRATEGY", symbol="BTC/USDT",
        htf="1D", mtf="4H", ltf="1H", state=CandidateState.RISK_GATE,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_target_price=115.0 # Target 115, Entry 100 (gain 15), SL 95 (risk 5) -> RR = 3.0 < 4.0 -> Reject!
    )
    ltf_payload = make_dummy_payload("1H", price=100.0)
    ltf_payload.structure_state.protected_low = make_dummy_sequence_swing(900, 95.0, SwingType.SWING_LOW, StructuralRole.PROTECTED_LOW)
    res = hyp.evaluate(cand, make_dummy_payload("1D"), make_dummy_payload("4H"), ltf_payload)
    assert res is not None and res.status == CandidateState.REJECTED.value
    assert "REJECT_RR_BELOW_4R" in res.rejection_reason


def test_max_account_risk_ceiling_1_percent():
    """Validates that risk sizing never exceeds 1.0% of current equity."""
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY",
        trade_plan_id="plan_risk_1",
        symbol="BTC/USDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=95.0, # 5.0 risk dist (5%)
        target_price=130.0, # 30.0 target dist -> RR = 6.0
        raw_rr=6.0,
        status="ENTERED"
    )
    acct = AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    cfg = RiskConfig(max_risk_fraction=0.01, min_rr_floor=4.0)
    res = RiskCoordinator.evaluate(plan, acct, config=cfg)
    assert isinstance(res, RiskApprovedPlan)
    assert res.dollar_risk <= 100.0 + 1e-6 # Exactly 1.0% of $10,000 = $100.0


def test_mtf_structural_trailing_monotonicity():
    """Validates that MTF structural trailing stop is monotonic and never widens risk."""
    from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
    
    atm = ActiveTradeManager(enable_mtf_trailing=True, enable_profit_lock=False)
    
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY",
        trade_plan_id="trade_trail_1",
        symbol="BTC/USDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0, # Initial SL = 90.0
        target_price=150.0,
        raw_rr=5.0,
        status="ENTERED"
    )
    atm.register_trade("trade_trail_1", plan)
    
    # 1. MTF forms higher protected low at 95.0 -> Trail stop moves to 95.0
    mtf_higher = make_dummy_payload("4H", price=110.0)
    mtf_higher.structure_state.protected_low = make_dummy_sequence_swing(1100, 95.0, SwingType.SWING_LOW, StructuralRole.PROTECTED_LOW)
    atm.evaluate(make_dummy_payload("1D"), mtf_higher, make_dummy_payload("1H", price=110.0))
    assert atm.active_trades["trade_trail_1"].stop_invalidation_price == 95.0
    
    # 2. MTF anomaly forms lower swing at 92.0 -> Monotonic ratchet IGNORES it and keeps 95.0!
    mtf_lower = make_dummy_payload("4H", price=112.0)
    mtf_lower.structure_state.protected_low = make_dummy_sequence_swing(1200, 92.0, SwingType.SWING_LOW, StructuralRole.PROTECTED_LOW)
    atm.evaluate(make_dummy_payload("1D"), mtf_lower, make_dummy_payload("1H", price=112.0))
    assert atm.active_trades["trade_trail_1"].stop_invalidation_price == 95.0
