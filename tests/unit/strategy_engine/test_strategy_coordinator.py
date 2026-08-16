import pytest
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from tests.unit.strategy_engine.test_bias_classifier import create_mock_payload
from market_intelligence.primitives import TrendDirection
from market_intelligence.phase_engine import MarketPhase

def test_strategy_coordinator_creates_candidates():
    # In EXPANSION phase, Continuation Riding candidate is tracked
    htf_exp = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    mtf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    ltf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    
    coordinator = StrategyCoordinator()
    plans = coordinator.evaluate(htf_exp, mtf, ltf)
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 1
    assert "HYP_B_CONTINUATION_RIDING" in [c.hypothesis_id for c in coordinator.candidate_tracker.active_candidates.values()]

    # In PULLBACK phase, Pullback Riding candidate is also tracked
    htf_pb = create_mock_payload(TrendDirection.BULLISH, MarketPhase.PULLBACK)
    plans = coordinator.evaluate(htf_pb, mtf, ltf)
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 2
    assert "HYP_A_PULLBACK_RIDING" in [c.hypothesis_id for c in coordinator.candidate_tracker.active_candidates.values()]

def test_strategy_coordinator_ignores_no_trade():
    # If we pass all neutral, it should just ignore and not spam rejections
    htf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    mtf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    ltf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    
    coordinator = StrategyCoordinator()
    plans = coordinator.evaluate(htf, mtf, ltf)
    
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 0
