"""
Phase 10.2 Unit Test: H_KZ_FRESH_01 HTF KeyZone Freshness Isolation
Verifies:
1. Invariance when enable_kz_freshness=False (stale zones not rejected by freshness gate)
2. Causal rejection when enable_kz_freshness=True and zone_age > threshold
3. Candidate transition to REJECTED with invalidation_reason="REJECT_KEYZONE_STALE_AGE"
4. Fresh zones (zone_age <= threshold) are preserved
"""

import pytest
from market_intelligence.primitives import MarketStatePayload, Candle, TrendDirection, MarketPhase
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.lifecycle.candidate_tracker import CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy


def make_dummy_payload(symbol="BTCUSD", timeframe="1H", timestamp=1000, current_price=100.0):
    return MarketStatePayload(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        current_price=current_price,
        current_candle=Candle(timestamp=timestamp, open=current_price, high=current_price+1, low=current_price-1, close=current_price, volume=100),
        events=[],
        swings=[],
        structure_state=None,
        liquidity_pools=[],
        keyzones=[],
        phase_state=MarketPhase.EXPANSION,
        trend_state=TrendDirection.BULLISH
    )


def test_kz_freshness_off_invariance():
    """When enable_kz_freshness=False, stale keyzones are NOT rejected by freshness gate."""
    strategy = UnifiedStrategy(enable_kz_freshness=False)
    
    # 20-day old zone
    creation_ts = 1_000_000
    interact_ts = creation_ts + (20 * 86400)
    
    candidate = CandidateSetup(
        candidate_id="cand_test_off",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_keyzone_id="OB_BULLISH_OB_1000000_SW_1",
        htf_kz_creation_timestamp=creation_ts,
        htf_interaction_timestamp=interact_ts
    )
    
    htf = make_dummy_payload("BTCUSD", "1D", interact_ts)
    mtf = make_dummy_payload("BTCUSD", "4H", interact_ts)
    ltf = make_dummy_payload("BTCUSD", "1H", interact_ts)
    
    strategy.evaluate(candidate, htf, mtf, ltf)
    
    # Candidate should NOT be rejected by freshness
    assert candidate.state == CandidateState.WAIT_MTF_ALIGNMENT
    assert candidate.invalidation_reason != "REJECT_KEYZONE_STALE_AGE"


def test_kz_freshness_on_rejects_stale_zone():
    """When enable_kz_freshness=True, zone older than threshold is rejected with REJECT_KEYZONE_STALE_AGE."""
    max_age_sec = 7 * 86400
    strategy = UnifiedStrategy(enable_kz_freshness=True, max_htf_kz_age_seconds=max_age_sec)
    
    # 10-day old zone (> 7 days)
    creation_ts = 1_000_000
    interact_ts = creation_ts + (10 * 86400)
    
    candidate = CandidateSetup(
        candidate_id="cand_test_stale",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_keyzone_id="OB_BULLISH_OB_1000000_SW_1",
        htf_kz_creation_timestamp=creation_ts,
        htf_interaction_timestamp=interact_ts
    )
    
    htf = make_dummy_payload("BTCUSD", "1D", interact_ts)
    mtf = make_dummy_payload("BTCUSD", "4H", interact_ts)
    ltf = make_dummy_payload("BTCUSD", "1H", interact_ts)
    
    plan = strategy.evaluate(candidate, htf, mtf, ltf)
    
    assert candidate.state == CandidateState.REJECTED
    assert candidate.invalidation_reason == "REJECT_KEYZONE_STALE_AGE"
    assert plan is not None
    assert plan.status == CandidateState.REJECTED.value
    assert plan.rejection_reason == "REJECT_KEYZONE_STALE_AGE"


def test_kz_freshness_on_preserves_fresh_zone():
    """When enable_kz_freshness=True, zone younger than threshold is preserved."""
    max_age_sec = 7 * 86400
    strategy = UnifiedStrategy(enable_kz_freshness=True, max_htf_kz_age_seconds=max_age_sec)
    
    # 3-day old zone (<= 7 days)
    creation_ts = 1_000_000
    interact_ts = creation_ts + (3 * 86400)
    
    candidate = CandidateSetup(
        candidate_id="cand_test_fresh",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSD",
        htf="1D", mtf="4H", ltf="1H",
        state=CandidateState.WAIT_MTF_ALIGNMENT,
        directional_permission=DirectionalPermission.PERMIT_LONG,
        htf_keyzone_id="OB_BULLISH_OB_1000000_SW_1",
        htf_kz_creation_timestamp=creation_ts,
        htf_interaction_timestamp=interact_ts
    )
    
    htf = make_dummy_payload("BTCUSD", "1D", interact_ts)
    mtf = make_dummy_payload("BTCUSD", "4H", interact_ts)
    ltf = make_dummy_payload("BTCUSD", "1H", interact_ts)
    
    strategy.evaluate(candidate, htf, mtf, ltf)
    
    assert candidate.state == CandidateState.WAIT_MTF_ALIGNMENT
    assert candidate.invalidation_reason != "REJECT_KEYZONE_STALE_AGE"
