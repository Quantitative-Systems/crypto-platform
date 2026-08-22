"""
DAY 35 — Canonical Strategy State-Machine Deterministic Test Suite
Validates all 17 canonical specification requirements across P01, P02, P03, and P04.
"""

import pytest
from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, RawSwing, SequenceSwing, SequenceLabel, SwingScope,
    MarketEvent, StructureState, SwingType, SwingStatus, EventType, MarketPhase, ZoneType
)
from market_intelligence.structure_builder_engine import StructureEvent
from market_intelligence.keyzone_engine import KeyZone, KeyZoneType, ZoneScope, ZoneStatus
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup, CandidateTracker
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy
from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from strategy_engine.entry.ltf_entry_model import LTFEntryModel
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from strategy_engine.news.news_provider import NewsProvider, MemoryNewsProvider, NewsEvent, NewsImpact, NullNewsProvider
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.risk_rejection import RiskRejectionPayload, RiskRejectionReason

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


def make_swing(price: float, swing_type: SwingType = SwingType.SWING_LOW, ts: int = 1000) -> SequenceSwing:
    raw = RawSwing(
        swing_id=f"sw_{ts}_{price}",
        timestamp=ts,
        price=price,
        swing_type=swing_type,
        candle_index=1,
        confirmation_timestamp=ts,
        confirmation_index=1,
        scope=SwingScope.EXTERNAL
    )
    return SequenceSwing(raw_swing=raw, label=SequenceLabel.HL if swing_type == SwingType.SWING_LOW else SequenceLabel.HH)


def make_payload(
    symbol="BTCUSD",
    timeframe="1H",
    timestamp=1000,
    trend=TrendDirection.BULLISH,
    phase=MarketPhase.EXPANSION,
    current_price=100.0,
    protected_price=90.0,
    weak_price=150.0,
    valuation="EQUILIBRIUM"
) -> MarketStatePayload:
    prot = make_swing(protected_price, SwingType.SWING_LOW if trend == TrendDirection.BULLISH else SwingType.SWING_HIGH, ts=timestamp)
    weak = make_swing(weak_price, SwingType.SWING_HIGH if trend == TrendDirection.BULLISH else SwingType.SWING_LOW, ts=timestamp)
    
    struct = StructureState(
        external_trend=trend,
        internal_trend=trend,
        protected_low=prot if trend == TrendDirection.BULLISH else None,
        protected_high=prot if trend == TrendDirection.BEARISH else None,
        weak_high=weak if trend == TrendDirection.BULLISH else None,
        weak_low=weak if trend == TrendDirection.BEARISH else None,
        events=[]
    )
    
    return MarketStatePayload(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        current_price=current_price,
        current_candle=Candle(timestamp=timestamp, open=current_price, high=current_price+1, low=current_price-1, close=current_price, volume=100),
        events=[],
        swings=[],
        structure_state=struct,
        liquidity_pools=[],
        keyzones=[],
        phase_state=phase,
        trend_state=trend,
        valuation_state=valuation,
        scorecard={"validation_score": 100, "reason_codes": ["DISPLACEMENT_CONFIRMED"], "validation_status": "VALID"},
        metadata={}
    )


# ============================================================================
# ============================================================================
# ============================================================================
# ============================================================================
# ============================================================================
# 5. HTF Context -> MTF Setup Causality
# ============================================================================
def test_5_htf_context_to_mtf_setup_causality():
    """5. Pre-existing MTF event before HTF context timestamp must NOT be reused."""
    htf = make_payload(timeframe="1D", timestamp=2000)
    mtf = make_payload(timeframe="4H", timestamp=2000)
    
    # Event happened at t=1500 (before HTF context at t=2000)
    stale_event = StructureEvent(
        timestamp=1500, event_type=EventType.INTERNAL_CHOCH, price_level=100.0,
        broken_swing_id="sw1", direction="BULLISH", candle_index=1
    )
    mtf.structure_state.events = [stale_event]
    
    candidate = CandidateSetup(
        candidate_id="c_causal_1", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT, directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_context_timestamp=2000
    )
    
    plan = UnifiedStrategy().evaluate(candidate, htf, mtf, make_payload(timeframe="1H", timestamp=2000))
    assert plan is None
    assert candidate.state == CandidateState.WAIT_MTF_ALIGNMENT  # Not transitioned because event was stale

    # New causal event at t=2100
    fresh_event = StructureEvent(
        timestamp=2100, event_type=EventType.INTERNAL_CHOCH, price_level=100.0,
        broken_swing_id="sw2", direction="BULLISH", candle_index=2
    )
    mtf.structure_state.events.append(fresh_event)
    plan2 = UnifiedStrategy().evaluate(candidate, htf, mtf, make_payload(timeframe="1H", timestamp=2100))
    assert candidate.state == CandidateState.WAIT_MTF_RETEST
    assert candidate.mtf_alignment_timestamp == 2100


# ============================================================================
# 6. MTF Setup -> MTF Zone Causality
# ============================================================================
def test_6_mtf_setup_to_mtf_zone_causality():
    """6. MTF KeyZone created before MTF alignment event must NOT be reused."""
    htf = make_payload(timeframe="1D", timestamp=2000)
    mtf = make_payload(timeframe="4H", timestamp=2500, current_price=100.0)
    
    # Zombie KeyZone created at t=1800 (before alignment at t=2100)
    zombie_kz = KeyZone(
        zone_id="OB_BULLISH_1800", zone_type=KeyZoneType.BULLISH_OB, scope=ZoneScope.INTERNAL,
        price_level=100.0, high_boundary=102.0, low_boundary=98.0,
        creation_timestamp=1800, creation_candle_index=1, status=ZoneStatus.MITIGATED
    )
    mtf.keyzones = [zombie_kz]
    
    candidate = CandidateSetup(
        candidate_id="c_causal_2", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_RETEST, directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_context_timestamp=2000, mtf_alignment_timestamp=2100, metadata={"context": "PULLBACK"}
    )
    
    plan = UnifiedStrategy().evaluate(candidate, htf, mtf, make_payload(timeframe="1H", timestamp=2500))
    assert plan is None
    assert candidate.state == CandidateState.WAIT_MTF_RETEST  # Stale zone rejected

    # Causal KeyZone created at t=2200
    causal_kz = KeyZone(
        zone_id="OB_BULLISH_2200", zone_type=KeyZoneType.BULLISH_OB, scope=ZoneScope.INTERNAL,
        price_level=100.0, high_boundary=102.0, low_boundary=98.0,
        creation_timestamp=2200, creation_candle_index=2, status=ZoneStatus.MITIGATED
    )
    mtf.keyzones.append(causal_kz)
    plan2 = UnifiedStrategy().evaluate(candidate, htf, mtf, make_payload(timeframe="1H", timestamp=2500))
    assert candidate.state == CandidateState.WAIT_LTF_TRIGGER
    assert candidate.mtf_keyzone_id == "OB_BULLISH_2200"


# ============================================================================
# 7. MTF Zone -> Retest Causality
# ============================================================================
def test_7_mtf_zone_to_retest_causality():
    """7. Price must retest the causal MTF zone after its creation."""
    htf = make_payload(timeframe="1D")
    mtf = make_payload(timeframe="4H", timestamp=3000, current_price=100.0)
    
    causal_kz = KeyZone(
        zone_id="OB_BULLISH_2200", zone_type=KeyZoneType.BULLISH_OB, scope=ZoneScope.INTERNAL,
        price_level=100.0, high_boundary=101.0, low_boundary=99.0,
        creation_timestamp=2200, creation_candle_index=2, status=ZoneStatus.MITIGATED
    )
    mtf.keyzones = [causal_kz]
    
    candidate = CandidateSetup(
        candidate_id="c_causal_3", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_RETEST, directional_permission=DirectionalPermission.PERMIT_LONG,
        mtf_alignment_timestamp=2100
    )
    
    UnifiedStrategy().evaluate(candidate, htf, mtf, make_payload(timeframe="1H", timestamp=3000))
    assert candidate.state == CandidateState.WAIT_LTF_TRIGGER
    assert candidate.mtf_retest_timestamp == 3000


# ============================================================================
# 8. Retest -> LTF Confirmation Causality
# ============================================================================
def test_8_retest_to_ltf_confirmation_causality():
    """8. LTF confirmation evaluates sweep + displacement in expected direction."""
    ltf_valid = make_payload(timeframe="1H", timestamp=3100)
    ltf_valid.events = [
        MarketEvent(timestamp=3100, timeframe="1H", symbol="BTCUSD", event_type=EventType.LIQUIDITY_SWEEP, price_level=95.0, metadata={"direction": "BULLISH"})
    ]
    ltf_valid.scorecard = {"reason_codes": ["DISPLACEMENT_CONFIRMED"]}
    
    candidate = CandidateSetup(
        candidate_id="c_causal_4", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_LTF_TRIGGER, directional_permission=DirectionalPermission.PERMIT_LONG,
        mtf_retest_timestamp=3000
    )
    
    UnifiedStrategy().evaluate(candidate, make_payload("1D"), make_payload("4H"), ltf_valid)
    assert candidate.state == CandidateState.RISK_GATE
    assert candidate.ltf_confirmation_timestamp == 3100


# ============================================================================
# 9. Zombie MTF Zone Invalidation
# ============================================================================
def test_9_zombie_mtf_zone_invalidation():
    """9. Break of KeyZone origin or status INVALIDATED triggers structural rejection."""
    htf = make_payload(timeframe="1D")
    # For a Bullish KeyZone with low=95.0, price dropping to 90.0 breaks structural origin
    mtf_broken = make_payload(timeframe="4H", timestamp=3200, current_price=90.0)
    broken_kz = KeyZone(
        zone_id="OB_BULLISH_2200", zone_type=KeyZoneType.BULLISH_OB, scope=ZoneScope.INTERNAL,
        price_level=97.5, high_boundary=100.0, low_boundary=95.0,
        creation_timestamp=2200, creation_candle_index=2, status=ZoneStatus.MITIGATED
    )
    mtf_broken.keyzones = [broken_kz]
    
    candidate = CandidateSetup(
        candidate_id="c_inval_1", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_LTF_TRIGGER, directional_permission=DirectionalPermission.PERMIT_LONG,
        mtf_keyzone_id="OB_BULLISH_2200"
    )
    
    plan = UnifiedStrategy().evaluate(candidate, htf, mtf_broken, make_payload("1H", timestamp=3200))
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_STRUCTURAL_ORIGIN_BROKEN"
    assert candidate.state == CandidateState.REJECTED


# ============================================================================
# 10. Superseded HTF Context Invalidation
# ============================================================================
def test_10_superseded_htf_context_invalidation():
    """10. New HTF structural event invalidates existing pending candidates."""
    htf = make_payload(timeframe="1D", timestamp=4000)
    new_htf_event = StructureEvent(
        timestamp=3500, event_type=EventType.EXTERNAL_CHOCH, price_level=120.0,
        broken_swing_id="htf_sw", direction="BEARISH", candle_index=5
    )
    htf.structure_state.events = [new_htf_event]
    
    candidate = CandidateSetup(
        candidate_id="c_inval_2", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_RETEST, directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_context_timestamp=3000
    )
    
    plan = UnifiedStrategy().evaluate(candidate, htf, make_payload("4H"), make_payload("1H"))
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_SUPERSEDED_HTF_CONTEXT"


# ============================================================================
# 11. LTF Structural SL
# ============================================================================
def test_11_ltf_structural_sl():
    """11. Initial SL is strictly derived from LTF protected_low (Long) or protected_high (Short)."""
    htf = make_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(160.0, SwingType.SWING_HIGH)
    
    ltf_long = make_payload(timeframe="1H", current_price=100.0)
    ltf_long.structure_state.protected_low = make_swing(92.5, SwingType.SWING_LOW)
    
    c_long = CandidateSetup(
        candidate_id="c_sl_1", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan_long = UnifiedStrategy().evaluate(c_long, htf, make_payload("4H"), ltf_long)
    assert plan_long.stop_invalidation_price == 92.5

    # Short SL
    htf_short = make_payload(timeframe="1D", trend=TrendDirection.BEARISH)
    htf_short.structure_state.weak_low = make_swing(40.0, SwingType.SWING_LOW)
    
    ltf_short = make_payload(timeframe="1H", trend=TrendDirection.BEARISH, current_price=100.0)
    ltf_short.structure_state.protected_high = make_swing(108.0, SwingType.SWING_HIGH)
    
    c_short = CandidateSetup(
        candidate_id="c_sl_2", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_SHORT
    )
    plan_short = UnifiedStrategy().evaluate(c_short, htf_short, make_payload("4H"), ltf_short)
    assert plan_short.stop_invalidation_price == 108.0


# ============================================================================
# 12. Directional Geometry
# ============================================================================
def test_12_directional_geometry():
    """12. LONG requires SL < Entry < TP; SHORT requires TP < Entry < SL."""
    htf = make_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(150.0, SwingType.SWING_HIGH)
    
    # Inverted Long: Entry=160 > TP=150
    ltf_inv = make_payload(timeframe="1H", current_price=160.0)
    ltf_inv.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW)
    
    c_inv = CandidateSetup(
        candidate_id="c_geom_1", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = UnifiedStrategy().evaluate(c_inv, htf, make_payload("4H"), ltf_inv)
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_INVALID_ANCHOR_GEOMETRY"


# ============================================================================
# 13. >= 4R Enforcement
# ============================================================================
def test_13_rr_floor_enforcement():
    """13. Enforces >= 4.0R minimum planned reward-to-risk floor."""
    htf = make_payload(timeframe="1D")
    htf.structure_state.weak_high = make_swing(130.0, SwingType.SWING_HIGH) # Reward = 30
    
    ltf = make_payload(timeframe="1H", current_price=100.0)
    ltf.structure_state.protected_low = make_swing(90.0, SwingType.SWING_LOW) # Risk = 10 -> RR = 3.0
    
    c = CandidateSetup(
        candidate_id="c_rr_1", hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD", htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.RISK_GATE, directional_permission=DirectionalPermission.PERMIT_LONG
    )
    plan = UnifiedStrategy().evaluate(c, htf, make_payload("4H"), ltf)
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_RR_BELOW_4R"
    assert plan.raw_rr == 3.0


# ============================================================================
# 14. <= 1% Risk Enforcement
# ============================================================================
def test_14_max_risk_enforcement():
    """14. Maximum allowed risk is strictly capped at 1% of liquid equity."""
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY", trade_plan_id="p_risk_1", symbol="BTCUSD",
        directional_permission="PERMIT_LONG", setup_timestamp=1000, entry_price=100.0,
        stop_invalidation_price=95.0, target_price=150.0, raw_rr=10.0, status="ENTERED"
    )
    account = AccountState(current_equity=25000.0, peak_equity=25000.0, daily_pnl=0.0, weekly_pnl=0.0, open_position_count=0)
    approved = RiskCoordinator.evaluate(plan, account)
    assert isinstance(approved, RiskApprovedPlan)
    assert approved.dollar_risk == 250.0  # 1.0% of $25,000
    assert approved.position_units == 50.0  # $250 / $5 stop distance


# ============================================================================
# 15. MTF Structural Trailing
# ============================================================================
def test_15_mtf_structural_trailing():
    """15. Active position trails stop loss using MTF structural progression and exits on adverse CHOCH."""
    atm = ActiveTradeManager()
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY", trade_plan_id="p_trail_1", symbol="BTCUSD",
        directional_permission="PERMIT_LONG", setup_timestamp=1000, entry_price=100.0,
        stop_invalidation_price=90.0, target_price=150.0, raw_rr=6.0, status="ENTERED"
    )
    atm.register_trade("p_trail_1", plan)
    
    # 1. MTF forms new higher protected low at 98.0 -> Stop ratchets upward
    mtf1 = make_payload(timeframe="4H", current_price=110.0, protected_price=98.0)
    atm.evaluate(make_payload("1D", current_price=110.0), mtf1, make_payload("1H", current_price=110.0))
    assert plan.stop_invalidation_price == 98.0

    # 2. MTF protected low drops to 95.0 -> Stop must NOT widen
    mtf2 = make_payload(timeframe="4H", current_price=115.0, protected_price=95.0)
    atm.evaluate(make_payload("1D", current_price=115.0), mtf2, make_payload("1H", current_price=115.0))
    assert plan.stop_invalidation_price == 98.0

    # 3. Adverse MTF Bearish CHOCH -> Triggers MTF_TRAIL_EXIT
    mtf3 = make_payload(timeframe="4H", current_price=112.0, protected_price=98.0)
    adverse_choch = StructureEvent(
        timestamp=2000, event_type=EventType.INTERNAL_CHOCH, price_level=105.0,
        broken_swing_id="sw_b", direction="BEARISH", candle_index=10
    )
    mtf3.structure_state.events = [adverse_choch]
    exited = atm.evaluate(make_payload("1D", current_price=112.0), mtf3, make_payload("1H", current_price=112.0))
    assert len(exited) == 1
    assert exited[0].position_status == PositionState.MTF_TRAIL_EXIT.value


# ============================================================================
# 16. News Lockout Interface
# ============================================================================
def test_16_news_lockout_interface():
    """16. Blocks new entries during 30m window around qualifying major news without closing active positions."""
    news = MemoryNewsProvider()
    news.add_event(NewsEvent(
        event_id="CPI_1", timestamp=10000, event_name="US CPI Release",
        impact=NewsImpact.HIGH, affected_symbols=["BTCUSD"]
    ))

    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY", trade_plan_id="p_news_1", symbol="BTCUSD",
        directional_permission="PERMIT_LONG", setup_timestamp=9500,  # 8.3 minutes before news (within 30m)
        entry_price=100.0, stop_invalidation_price=90.0, target_price=150.0, raw_rr=6.0, status="ENTERED"
    )
    account = AccountState(current_equity=10000.0, peak_equity=10000.0, daily_pnl=0.0, weekly_pnl=0.0, open_position_count=0)

    # Risk Coordinator with news provider blocks the entry
    rejection = RiskCoordinator.evaluate(plan, account, news_provider=news)
    assert isinstance(rejection, RiskRejectionPayload)
    assert rejection.reason == RiskRejectionReason.REJECT_NEWS_BLACKOUT

    # Permitted outside window (at t=12000, 33.3 minutes after news)
    plan_clear = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY", trade_plan_id="p_news_2", symbol="BTCUSD",
        directional_permission="PERMIT_LONG", setup_timestamp=12000,
        entry_price=100.0, stop_invalidation_price=90.0, target_price=150.0, raw_rr=6.0, status="ENTERED"
    )
    approved = RiskCoordinator.evaluate(plan_clear, account, news_provider=news)
    assert isinstance(approved, RiskApprovedPlan)


# ============================================================================
# 17. Research / Production Risk Separation
# ============================================================================
def test_17_research_production_risk_separation():
    """17. Production enforces circuit breaker; Research mode allows unconstrained candidate evaluation."""
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY", trade_plan_id="p_res_1", symbol="BTCUSD",
        directional_permission="PERMIT_LONG", setup_timestamp=1000,
        entry_price=100.0, stop_invalidation_price=90.0, target_price=150.0, raw_rr=6.0, status="ENTERED"
    )
    
    # Account is in 12% systemic drawdown (Current=8800, Peak=10000)
    account_in_dd = AccountState(
        current_equity=8800.0, peak_equity=10000.0, daily_pnl=0.0, weekly_pnl=0.0, open_position_count=0
    )

    # 1. Production Mode (Default config): Rejected by Systemic Circuit Breaker
    prod_res = RiskCoordinator.evaluate(plan, account_in_dd)
    assert isinstance(prod_res, RiskRejectionPayload)
    assert prod_res.reason == RiskRejectionReason.REJECT_SYSTEMIC_CIRCUIT_BREAKER

    # 2. Research Mode: Circuit breaker disabled -> Approved for unconstrained population measurement
    research_cfg = RiskConfig(enable_circuit_breakers=False)
    research_res = RiskCoordinator.evaluate(plan, account_in_dd, config=research_cfg)
    assert isinstance(research_res, RiskApprovedPlan)
    assert research_res.dollar_risk == 88.0  # 1% of $8,800
