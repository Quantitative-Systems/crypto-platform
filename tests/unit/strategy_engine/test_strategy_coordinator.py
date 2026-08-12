import pytest
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from tests.unit.strategy_engine.test_bias_classifier import create_mock_payload
from market_intelligence.primitives import TrendDirection
from market_intelligence.phase_engine import MarketPhase

def test_strategy_coordinator_creates_candidates():
    htf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    mtf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    ltf = create_mock_payload(TrendDirection.BULLISH, MarketPhase.EXPANSION)
    
    coordinator = StrategyCoordinator()
    
    # Run 1: Should create candidates since bias is PERMIT_LONG
    plans = coordinator.evaluate(htf, mtf, ltf)
    
    # No plans returned yet because they are pending in WAIT_MTF_ALIGNMENT
    assert len(plans) == 0
    
    # Verify candidates are being tracked
    assert len(coordinator.candidate_tracker.active_candidates) == 2

def test_strategy_coordinator_ignores_no_trade():
    # If we pass all neutral, it should just ignore and not spam rejections
    htf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    mtf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    ltf = create_mock_payload(TrendDirection.NEUTRAL, MarketPhase.ACCUMULATION)
    
    coordinator = StrategyCoordinator()
    plans = coordinator.evaluate(htf, mtf, ltf)
    
    assert len(plans) == 0
    assert len(coordinator.candidate_tracker.active_candidates) == 0
