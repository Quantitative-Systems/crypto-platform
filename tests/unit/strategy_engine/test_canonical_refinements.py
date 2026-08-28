"""
Unit tests for Day 35 Canonical Refinements:
1. Candidate Setup Lifespan Expiration
2. Dual Active Trade Management (MTF Trailing + +1.0R Profit-Lock Ratchet)
3. Planned RR Hurdle Validation
"""

import pytest
from strategy_engine.contracts.strategy_state import CandidateState, PositionState
from strategy_engine.contracts.trade_plan import DirectionalPermission, TradePlanPayload
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup, CandidateTracker
from strategy_engine.lifecycle.active_trade_manager import ActiveTradeManager
from market_intelligence.primitives import MarketStatePayload, Candle, TrendDirection


from market_intelligence.primitives import (
    MarketStatePayload, Candle, TrendDirection, MarketPhase,
    StructureState, SequenceSwing, RawSwing, SwingType, SwingScope, SequenceLabel
)


def make_payload(timeframe: str = "1H", current_price: float = 100.0, timestamp: int = 1000) -> MarketStatePayload:
    raw = RawSwing(
        swing_id=f"sw_{timestamp}_{current_price}",
        timestamp=timestamp,
        price=current_price - 10.0,
        swing_type=SwingType.SWING_LOW,
        candle_index=1,
        confirmation_timestamp=timestamp,
        confirmation_index=1,
        scope=SwingScope.EXTERNAL
    )
    prot = SequenceSwing(raw_swing=raw, label=SequenceLabel.HL)
    struct = StructureState(
        external_trend=TrendDirection.BULLISH,
        internal_trend=TrendDirection.BULLISH,
        protected_low=prot,
        protected_high=None,
        weak_high=None,
        weak_low=None,
        events=[]
    )
    return MarketStatePayload(
        symbol="BTCUSDT",
        timeframe=timeframe,
        timestamp=timestamp,
        current_price=current_price,
        current_candle=Candle(timestamp=timestamp, open=current_price, high=current_price+1, low=current_price-1, close=current_price, volume=100.0),
        events=[],
        swings=[],
        structure_state=struct,
        liquidity_pools=[],
        keyzones=[],
        phase_state=MarketPhase.EXPANSION,
        trend_state=TrendDirection.BULLISH
    )


def test_candidate_lifespan_expiration():
    tracker = CandidateTracker()
    
    candidate = CandidateSetup(
        candidate_id="cand_test_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        htf="4H",
        mtf="1H",
        ltf="15M",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        creation_timestamp=1000,
        max_lifespan_seconds=3600 # 1 hour
    )
    tracker.add_candidate(candidate)
    
    # 1. At t=2000 (1000s elapsed < 3600s), candidate is NOT expired
    assert not candidate.is_expired(2000)
    pruned = tracker.prune_expired(2000)
    assert len(pruned) == 0
    assert len(tracker.get_active_candidates("BTCUSDT", "UNIFIED_STRATEGY")) == 1
    
    # 2. At t=5000 (4000s elapsed > 3600s), candidate is expired and pruned
    assert candidate.is_expired(5000)
    pruned = tracker.prune_expired(5000)
    assert len(pruned) == 1
    assert pruned[0].candidate_id == "cand_test_1"
    assert pruned[0].invalidation_reason == "REJECT_SETUP_LIFESPAN_EXPIRED"
    assert len(tracker.get_active_candidates("BTCUSDT", "UNIFIED_STRATEGY")) == 0


def test_profit_lock_ratchet_long():
    atm = ActiveTradeManager(
        enable_mtf_trailing=False,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75
    )
    
    plan = TradePlanPayload(
        hypothesis_id="UNIFIED_STRATEGY",
        trade_plan_id="plan_long_1",
        symbol="BTCUSDT",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1000,
        entry_price=100.0,
        stop_invalidation_price=90.0, # 10.0 risk distance
        target_price=150.0,
        raw_rr=5.0,
        status="ENTERED"
    )
    atm.register_trade("plan_long_1", plan)
    
    # Bar 1: Price reaches 105.0 (+0.5R) -> profit lock NOT triggered yet
    ltf1 = make_payload(timeframe="15M", current_price=105.0)
    ltf1.current_candle = Candle(timestamp=1000, open=100.0, high=105.0, low=99.0, close=105.0, volume=100.0)
    atm.evaluate(make_payload("4H", 105.0), make_payload("1H", 105.0), ltf1)
    assert plan.stop_invalidation_price == 90.0
    
    # Bar 2: Price reaches 112.0 (+1.2R >= 1.0R) -> Profit lock triggers!
    # Floor stop = 112.0 - (0.75 * 10) = 104.5 (+0.45R secured)
    ltf2 = make_payload(timeframe="15M", current_price=112.0)
    ltf2.current_candle = Candle(timestamp=2000, open=105.0, high=112.0, low=105.0, close=111.0, volume=100.0)
    atm.evaluate(make_payload("4H", 112.0), make_payload("1H", 112.0), ltf2)
    assert plan.stop_invalidation_price == pytest.approx(104.5, 0.01)
    
    # Bar 3: Price retraces to 104.0 -> SL hit at 104.5 (Profitable exit!)
    ltf3 = make_payload(timeframe="15M", current_price=104.0)
    ltf3.current_candle = Candle(timestamp=3000, open=111.0, high=111.0, low=104.0, close=104.0, volume=100.0)
    exited = atm.evaluate(make_payload("4H", 104.0), make_payload("1H", 104.0), ltf3)
    assert len(exited) == 1
    assert exited[0].position_status == PositionState.LTF_SL_EXIT.value
