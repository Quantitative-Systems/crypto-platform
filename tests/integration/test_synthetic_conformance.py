"""
SYNTHETIC STRATEGY CONFORMANCE SUITE (SC-01 .. SC-06)
=====================================================
Contract-level verification of the canonical HTF-Bias -> MTF-Setup -> LTF-Entry
concept (Pullback Riding / Continuation Riding) across P02/P03/P04.

Each scenario asserts STATE TRANSITIONS and canonical OUTPUTS, not merely
"function returned successfully".

  SC-01 MTF MISALIGNMENT   : HTF bullish, MTF bearish      -> NO ENTRY, candidate
                              remains WAIT_MTF_ALIGNMENT.
  SC-02 LTF MISALIGNMENT   : HTF+MTF aligned, LTF lacks
                              sweep/displacement            -> NO ENTRY, candidate
                              stops at WAIT_LTF_TRIGGER.
  SC-03 RR FILTER          : valid stack but planned RR<4   -> REJECT_RR_BELOW_4R.
  SC-04 VALID SETUP        : full stack qualifies, RR>=4    -> ENTERED, risk <= 1%.
  SC-05 TRAILING LOCK      : MTF structural trailing stop ratchets monotonically
                              and NEVER widens risk.
  SC-06 INTRABAR COLLISION : SL and TP touched in one bar   -> adverse-first SL exit.
"""

import pytest
from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, RawSwing, SequenceSwing, SequenceLabel,
    SwingScope, MarketEvent, StructureState, SwingType, EventType, MarketPhase,
)
from market_intelligence.structure_builder_engine import StructureEvent
from market_intelligence.keyzone_engine import KeyZone, KeyZoneType, ZoneScope, ZoneStatus
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from research.simulation.execution_simulator import ExecutionSimulator
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_swing(price: float, swing_type: SwingType = SwingType.SWING_LOW, ts: int = 1000) -> SequenceSwing:
    raw = RawSwing(
        swing_id=f"sw_{ts}_{price}", timestamp=ts, price=price, swing_type=swing_type,
        candle_index=1, confirmation_timestamp=ts, confirmation_index=1, scope=SwingScope.EXTERNAL,
    )
    label = SequenceLabel.HL if swing_type == SwingType.SWING_LOW else SequenceLabel.HH
    return SequenceSwing(raw_swing=raw, label=label)


def make_payload(
    timeframe: str = "1H", timestamp: int = 1000,
    trend: TrendDirection = TrendDirection.BULLISH,
    phase: MarketPhase = MarketPhase.EXPANSION,
    current_price: float = 100.0,
    protected_price: float = 90.0,
    weak_price: float = 150.0,
    symbol: str = "BTCUSD",
) -> MarketStatePayload:
    prot = make_swing(protected_price, SwingType.SWING_LOW if trend == TrendDirection.BULLISH else SwingType.SWING_HIGH, ts=timestamp)
    weak = make_swing(weak_price, SwingType.SWING_HIGH if trend == TrendDirection.BULLISH else SwingType.SWING_LOW, ts=timestamp)
    struct = StructureState(
        external_trend=trend, internal_trend=trend,
        protected_low=prot if trend == TrendDirection.BULLISH else None,
        protected_high=prot if trend == TrendDirection.BEARISH else None,
        weak_high=weak if trend == TrendDirection.BULLISH else None,
        weak_low=weak if trend == TrendDirection.BEARISH else None,
        events=[],
    )
    return MarketStatePayload(
        symbol=symbol, timeframe=timeframe, timestamp=timestamp, current_price=current_price,
        current_candle=Candle(timestamp=timestamp, open=current_price, high=current_price + 1,
                              low=current_price - 1, close=current_price, volume=100),
        events=[], swings=[], structure_state=struct, liquidity_pools=[], keyzones=[],
        phase_state=phase, trend_state=trend, valuation_state="EQUILIBRIUM",
        scorecard={"validation_score": 100, "reason_codes": ["DISPLACEMENT_CONFIRMED"], "validation_status": "VALID"},
        metadata={},
    )


def bearish_event(ts: int) -> StructureEvent:
    return StructureEvent(timestamp=ts, event_type=EventType.EXTERNAL_CHOCH, price_level=95.0,
                          broken_swing_id=f"sw_bear_{ts}", direction="BEARISH", candle_index=1)


def bullish_mtf_event(ts: int) -> StructureEvent:
    return StructureEvent(timestamp=ts, event_type=EventType.INTERNAL_CHOCH, price_level=100.0,
                          broken_swing_id=f"sw_{ts}", direction="BULLISH", candle_index=1)


def causal_mtf_keyzone(ts: int) -> KeyZone:
    return KeyZone(
        zone_id=f"KZ_BULL_{ts}", zone_type=KeyZoneType.BULLISH_OB, scope=ZoneScope.INTERNAL,
        price_level=100.0, high_boundary=102.0, low_boundary=98.0,
        creation_timestamp=ts, creation_candle_index=1, status=ZoneStatus.MITIGATED,
    )


# ---------------------------------------------------------------------------
# SC-01 MTF MISALIGNMENT -> NO ENTRY
# ---------------------------------------------------------------------------
def test_sc01_mtf_misalignment_no_entry():
    """
    HTF = BULLISH (bias allows long)
    MTF = BEARISH (no bullish alignment event exists)
    LTF = BULLISH
    Expected: candidate spawned but NEVER leaves WAIT_MTF_ALIGNMENT; no ENTERED plan.
    """
    coordinator = StrategyCoordinator()
    htf = make_payload(timeframe="1D", timestamp=1000, trend=TrendDirection.BULLISH)
    mtf = make_payload(timeframe="4H", timestamp=1000, trend=TrendDirection.BEARISH, current_price=100.0)
    mtf.structure_state.events = [bearish_event(900)]  # bearish shift only
    ltf = make_payload(timeframe="1H", timestamp=1000, trend=TrendDirection.BULLISH)

    plans = coordinator.evaluate(htf, mtf, ltf)
    plans += coordinator.evaluate(htf, mtf, ltf)

    assert all(p.status != CandidateState.ENTERED.value for p in plans)
    cands = coordinator.candidate_tracker.get_active_candidates("BTCUSD", "UNIFIED_STRATEGY")
    assert cands, "candidate must be alive (not spuriously rejected)"
    assert all(c.state == CandidateState.WAIT_MTF_ALIGNMENT for c in cands)


# ---------------------------------------------------------------------------
# SC-02 LTF MISALIGNMENT -> NO ENTRY
# ---------------------------------------------------------------------------
def test_sc02_ltf_misalignment_no_entry():
    """
    HTF bullish + MTF aligned + retest achieved, but LTF shows NO liquidity sweep,
    so candidate must arrest at WAIT_LTF_TRIGGER and never emit an entry.
    """
    coordinator = StrategyCoordinator()
    htf = make_payload(timeframe="1D", timestamp=1000, trend=TrendDirection.BULLISH)
    mtf = make_payload(timeframe="4H", timestamp=1200, trend=TrendDirection.BULLISH, current_price=100.0)
    mtf.structure_state.events = [bullish_mtf_event(1100)]
    mtf.keyzones = [causal_mtf_keyzone(1150)]
    ltf = make_payload(timeframe="1H", timestamp=1200, trend=TrendDirection.BULLISH)
    ltf.scorecard = {"reason_codes": []}  # no displacement confirmation

    plans = coordinator.evaluate(htf, mtf, ltf)          # spawn + align
    plans += coordinator.evaluate(htf, mtf, ltf)          # retest -> WAIT_LTF_TRIGGER
    plans += coordinator.evaluate(htf, mtf, ltf)          # LTF trigger check (fails)

    assert all(p.status != CandidateState.ENTERED.value for p in plans)
    cands = coordinator.candidate_tracker.get_active_candidates("BTCUSD", "UNIFIED_STRATEGY")
    assert cands
    assert all(c.state == CandidateState.WAIT_LTF_TRIGGER for c in cands)
    assert LTFEntryModel.evaluate(ltf, "BULLISH") is False


# ---------------------------------------------------------------------------
# SC-03 RR FILTER -> planned RR < 4.0 must be rejected
# ---------------------------------------------------------------------------
def test_sc03_rr_below_4_rejected():
    """
    HTF/MTF/LTF all qualify for a long, but structural anchors yield RR = 3.0,
    below the canonical 4.0R floor -> REJECT_RR_BELOW_4R, never ENTERED.
    """
    htf = make_payload(timeframe="1D", timestamp=1000, trend=TrendDirection.BULLISH, weak_price=130.0)
    ltf = make_payload(timeframe="1H", timestamp=1000, trend=TrendDirection.BULLISH, current_price=100.0)
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW, ts=1000)
    # Risk = 10, Reward = 30 -> RR = 3.0 < 4.0

    candidate = CandidateSetup(
        candidate_id="c_sc03", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG,
    )
    candidate.htf_target_price = 130.0  # HTF Context target_anchor_price from weak_high

    plan = UnifiedStrategy().evaluate(candidate, htf, make_payload(timeframe="4H", timestamp=1000), ltf)
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_RR_BELOW_4R"
# ---------------------------------------------------------------------------
# SC-04 VALID SETUP -> ENTRY with RR >= 4.0 and risk <= 1%
# ---------------------------------------------------------------------------
def test_sc04_valid_setup_entry_and_risk_cap():
    """
    Full canonical stack qualifies (RR = 5.0 >= 4.0). The plan must ENTER, and
    the P03 risk firewall must size risk at exactly <= 1.0% of account equity.
    """
    htf = make_payload(timeframe="1D", timestamp=1000, trend=TrendDirection.BULLISH, weak_price=150.0)
    ltf = make_payload(timeframe="1H", timestamp=1000, trend=TrendDirection.BULLISH, current_price=100.0)
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW, ts=1000)
    # Risk = 10, Reward = 50 -> RR = 5.0 >= 4.0

    candidate = CandidateSetup(
        candidate_id="c_sc04", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG,
    )
    candidate.htf_target_price = 150.0  # HTF Context target_anchor_price from weak_high

    plan = UnifiedStrategy().evaluate(candidate, htf, make_payload(timeframe="4H", timestamp=1000), ltf)
    assert plan is not None
    assert plan.status == CandidateState.ENTERED.value
    assert plan.raw_rr == pytest.approx(5.0)

    account = AccountState(current_equity=10000.0, peak_equity=10000.0,
                           daily_pnl=0.0, weekly_pnl=0.0, open_position_count=0)
    risk_result = RiskCoordinator.evaluate(plan, account)
    assert isinstance(risk_result, RiskApprovedPlan)
    assert risk_result.dollar_risk <= 0.01 * account.current_equity


# ---------------------------------------------------------------------------
# SC-05 TRAILING LOCK -> MTF structural trailing is monotonic, never widens
# ---------------------------------------------------------------------------
def test_sc05_mtf_trailing_lock_monotonic():
    """
    A registered long trade must have its stop ratchet upward as MTF protected
    lows rise, and MUST NEVER widen when MTF protected lows pull back.
    """
    atm = ActiveTradeManager(enable_mtf_trailing=True, enable_profit_lock=False)
    plan = TradePlanPayload(
        trade_plan_id="c_sc05", hypothesis_id="UNIFIED_STRATEGY", symbol="BTCUSD",
        directional_permission=DirectionalPermission.PERMIT_LONG.value,
        setup_timestamp=1000, entry_price=100.0,
        stop_invalidation_price=90.0, target_price=150.0, raw_rr=5.0,
        status=CandidateState.ENTERED.value,
    )
    atm.register_trade("c_sc05", plan)
    assert plan.stop_invalidation_price == 90.0

    # MTF protected low rises to 96 -> stop must ratchet up
    mtf_up = make_payload(timeframe="4H", timestamp=1500, trend=TrendDirection.BULLISH, protected_price=96.0)
    ltf = make_payload(timeframe="1H", timestamp=1500, trend=TrendDirection.BULLISH, current_price=105.0)
    atm.evaluate(make_payload("1D", timestamp=1500), mtf_up, ltf)
    assert plan.stop_invalidation_price == pytest.approx(96.0)

    # MTF protected low pulls back to 94 -> stop must NEVER widen back down
    mtf_down = make_payload(timeframe="4H", timestamp=2000, trend=TrendDirection.BULLISH, protected_price=94.0)
    ltf2 = make_payload(timeframe="1H", timestamp=2000, trend=TrendDirection.BULLISH, current_price=110.0)
    atm.evaluate(make_payload("1D", timestamp=2000), mtf_down, ltf2)
    assert plan.stop_invalidation_price == pytest.approx(96.0)


# ---------------------------------------------------------------------------
# SC-06 INTRABAR COLLISION -> adverse-first, SL wins over TP
# ---------------------------------------------------------------------------
def test_sc06_intrabar_collision_sl_precedence():
    """
    One candle touches BOTH stop and target. Because fill ordering is unknown,
    the conservative baseline axiom is ADVERSE-FIRST: the trade exits via SL.
    """
    sim = ExecutionSimulator()
    ledger = TradeLedger()
    trade = SimulatedTrade(
        trade_id="c_sc06", hypothesis_id="UNIFIED_STRATEGY", symbol="BTCUSD", timeframe_set="SET_3",
        directional_permission="PERMIT_LONG", setup_timestamp=1000,
        entry_price=100.0, fill_entry_price=100.0,
        initial_stop_price=90.0, current_stop_price=90.0, target_price=150.0,
        position_units=1.0, dollar_risk=10.0, status="ACTIVE",
    )
    ledger.trades["c_sc06"] = trade

    ambiguous_bar = Candle(timestamp=2000, open=100.0, high=160.0, low=85.0, close=110.0, volume=100.0)
    closed = sim.process_candle(ambiguous_bar, ledger)

    assert len(closed) == 1
    assert closed[0].status == "CLOSED"
    assert closed[0].exit_reason == "INITIAL_LTF_SL"  # SL precedence, NOT HTF_TP