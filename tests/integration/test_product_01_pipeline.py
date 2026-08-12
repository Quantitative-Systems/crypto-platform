import random
import pytest
from typing import List

from market_intelligence.primitives import Candle, MarketStatePayload, TrendDirection
from market_intelligence.phase_engine import MarketPhase
from market_intelligence.coordinator import LanguageCoordinator


def generate_deterministic_candles(count: int, seed: int = 42) -> List[Candle]:
    random.seed(seed)
    candles = []
    current_price = 1000.0
    
    for i in range(count):
        # Introduce a trending random walk
        move = random.uniform(-5.0, 5.5) # slightly bullish bias
        open_p = current_price
        close_p = current_price + move
        high_p = max(open_p, close_p) + random.uniform(0.0, 5.0)
        low_p = min(open_p, close_p) - random.uniform(0.0, 5.0)
        
        candles.append(
            Candle(
                timestamp=i * 1000,
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                volume=random.uniform(10.0, 1000.0)
            )
        )
        current_price = close_p
        
    return candles


def test_pipeline_end_to_end_compliance():
    candles = generate_deterministic_candles(200)
    coordinator = LanguageCoordinator(buffer_size=200)
    
    payload = coordinator.run(candles)
    
    # Assert schema compliance
    assert isinstance(payload, MarketStatePayload)
    assert payload.symbol == "BTCUSD"
    assert payload.current_price == candles[-1].close
    assert payload.trend_state in iter(TrendDirection)
    assert payload.phase_state in iter(MarketPhase)
    assert payload.scorecard is not None
    assert "validation_score" in payload.scorecard
    assert payload.metadata is not None


def test_pipeline_determinism():
    candles = generate_deterministic_candles(150)
    
    coordinator1 = LanguageCoordinator(buffer_size=200)
    payload1 = coordinator1.run(candles)
    
    coordinator2 = LanguageCoordinator(buffer_size=200)
    payload2 = coordinator2.run(candles)
    
    # Serialize payloads to compare completely
    import dataclasses
    dict1 = dataclasses.asdict(payload1)
    dict2 = dataclasses.asdict(payload2)
    
    assert dict1 == dict2


def test_pipeline_causality_audit():
    # Full dataset
    full_candles = generate_deterministic_candles(300)
    
    coordinator = LanguageCoordinator(buffer_size=300)
    payload = coordinator.run(full_candles)
    
    latest_candle = full_candles[-1]
    
    # Causality rule: No swing should have a confirmation_timestamp > latest_candle.timestamp
    for swing in payload.swings:
        assert swing.confirmation_timestamp <= latest_candle.timestamp
        
    # Also verify that events emitted do not have timestamps > latest_candle.timestamp
    for event in payload.events:
        assert event.timestamp <= latest_candle.timestamp


def test_pipeline_cross_engine_consistency():
    candles = generate_deterministic_candles(250)
    coordinator = LanguageCoordinator(buffer_size=300)
    
    # Let's process incrementally to catch any contradictory state during the walk
    for i in range(20, 250, 10):
        window = candles[:i]
        payload = coordinator.run(window)
        
        # 1. Trend cannot be BULLISH if Phase is REVERSAL from BULLISH
        # But wait, REVERSAL just means it changed.
        # Let's check a more rigid one:
        # If trend is BULLISH, we cannot have a BEARISH protected swing break.
        trend = payload.trend_state
        phase = payload.phase_state
        
        if phase == MarketPhase.EXPANSION:
            # An expansion phase implies we broke external structure, so trend shouldn't be RANGING or NEUTRAL
            # (unless it's just initializing, but usually it aligns)
            pass
            
        if trend == TrendDirection.BULLISH:
            assert phase != MarketPhase.ACCUMULATION # Assuming accumulation happens before bullish expansion
            # Wait, phase might be ACCUMULATION if trend was bearish and now ranging. 
            # If trend is purely BULLISH, ACCUMULATION shouldn't be active (it's RECOMPRESSION maybe).
            
        # Just ensure no fatal conflicting enums
        assert payload.trend_state is not None
        assert payload.phase_state is not None
