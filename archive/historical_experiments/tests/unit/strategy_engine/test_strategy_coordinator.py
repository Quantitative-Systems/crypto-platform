import pytest
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from tests.unit.strategy_engine.test_bias_classifier import create_mock_payload
from market_intelligence.primitives import TrendDirection
from market_intelligence.phase_engine import MarketPhase

from market_intelligence.primitives import KeyZone

def test_strategy_coordinator_requires_htf_keyzone_interaction():
    # Without HTF keyzone, no candidate is spawned even if bias is bullish
    htf_no_kz = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    mtf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    ltf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)

    coordinator = StrategyCoordinator()
    plans = coordinator.evaluate(htf_no_kz, mtf, ltf)
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 0

    # With active HTF Bullish KeyZone interaction at current_price (100.0), candidate is tracked
    kz = KeyZone(
        zone_id="KZ_HTF_BULLISH_1",
        zone_type="BULLISH_OB",
        direction=TrendDirection.BULLISH,
        high=105.0,
        low=95.0,
        timeframe="1D",
        creation_timestamp=500,
        is_mitigated=False
    )
    htf_with_kz = create_mock_payload(TrendDirection.BULLISH, MarketPhase.PULLBACK)
    htf_with_kz.keyzones = [kz]

    plans = coordinator.evaluate(htf_with_kz, mtf, ltf)
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 1
    assert "UNIFIED_STRATEGY" in [c.hypothesis_id for c in coordinator.candidate_tracker.active_candidates.values()]

    # If we evaluate again while candidate is already active, no duplicate is spawned
    plans2 = coordinator.evaluate(htf_with_kz, mtf, ltf)
    assert len(plans2) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 1

def test_strategy_coordinator_ignores_no_trade():
    # If we pass all neutral, it should just ignore and not spam rejections
    htf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    mtf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    ltf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    
    coordinator = StrategyCoordinator()
    plans = coordinator.evaluate(htf, mtf, ltf)
    
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 0
