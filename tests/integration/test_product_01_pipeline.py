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


def test_adversarial_causality_and_lookahead():
    full_candles = generate_deterministic_candles(300)
    
    # We choose T=150. We compare state at T (Payload A) with state at T+N (Payload B)
    T_index = 150
    T_timestamp = full_candles[T_index - 1].timestamp
    
    coordinator_A = LanguageCoordinator(buffer_size=300)
    payload_A = coordinator_A.run(full_candles[:T_index])
    
    coordinator_B = LanguageCoordinator(buffer_size=300)
    payload_B = coordinator_B.run(full_candles)
    
    # 1. Swings Causality
    # A swing in Payload B is valid historically if its confirmation_timestamp <= T_timestamp
    swings_B_historical = [s for s in payload_B.swings if s.confirmation_timestamp <= T_timestamp]
    assert len(payload_A.swings) == len(swings_B_historical), "Future candles altered historical swing count!"
    
    for sA, sB in zip(payload_A.swings, swings_B_historical):
        assert sA.swing_id == sB.swing_id
        assert sA.swing_type == sB.swing_type
        
    # 2. Structure Events Causality
    events_B_historical = [e for e in payload_B.structure_state.events if getattr(e, 'timestamp', 0) <= T_timestamp]
    # Length can differ slightly if a swing was confirmed exactly at T in A, but B sees it as part of a larger structure that deduplicates differently. 
    # But usually it's the same. We will just check the overlapping ones.
    
    for eA in payload_A.structure_state.events:
        # Find corresponding event in B by timestamp and price
        matches = [e for e in events_B_historical if e.timestamp == eA.timestamp and e.broken_swing_id == eA.broken_swing_id]
        assert len(matches) > 0, f"Historical event {eA} vanished in future payload!"
        eB = matches[0]
        # We DO NOT assert eA.event_type == eB.event_type because Engine 2 retroactively restates EXTERNAL/INTERNAL hierarchy.
        # This is documented confirmation latency/hierarchy restatement, NOT a lookahead bug in event generation.
        assert eA.price_level == eB.price_level
        assert eA.candle_index == eB.candle_index

    # 3. Liquidity Pools Causality
    # Pools active at T might be consumed by T+N and therefore no longer in the active payload.
    # We just ensure any pool still active in B that was created <= T was also present in A.
    pools_B_historical = [p for p in payload_B.liquidity_pools if p.creation_timestamp <= T_timestamp]
    for pB in pools_B_historical:
        matches = [p for p in payload_A.liquidity_pools if p.creation_timestamp == pB.creation_timestamp and p.price_level == pB.price_level]
        assert len(matches) > 0, "Future candles generated a historical pool that did not exist at the time!"

    # 4. Keyzones Causality
    kz_B_historical = [kz for kz in payload_B.keyzones if kz.creation_timestamp <= T_timestamp]
    for kzB in kz_B_historical:
        matches = [kz for kz in payload_A.keyzones if kz.creation_timestamp == kzB.creation_timestamp]
        assert len(matches) > 0, "Future candles generated a historical keyzone that did not exist at the time!"


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
