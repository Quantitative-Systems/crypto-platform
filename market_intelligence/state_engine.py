"""
Product 01: Crypto Platform - Market State Consolidation Engine
Aggregates Ontology, KeyZones, and Liquidity into a unified MarketStatePayload.
"""

from typing import List, Optional
from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, EventType
)
from market_intelligence.ontology import UniversalOntologyEngine
from market_intelligence.keyzones import KeyZoneEngine
from market_intelligence.liquidity import LiquidityEngine, LiquidityPool, LiquiditySweep


class MarketStateEngine:

    def __init__(self, swing_lookback: int = 2):
        self.ontology_engine = UniversalOntologyEngine(swing_lookback=swing_lookback)

    def evaluate(self, candles: List[Candle], symbol: str = "BTC/USDT", timeframe: str = "1D") -> MarketStatePayload:
        """Runs all market intelligence detectors and returns a consolidated state payload."""
        
        # 1. Evaluate Structure, Swings, BOS/CHOCH & Protected Anchors
        state = self.ontology_engine.evaluate_structure(candles, symbol=symbol, timeframe=timeframe)

        # 2. Detect KeyZones (Order Blocks & Fair Value Gaps)
        obs = KeyZoneEngine.detect_order_blocks(candles)
        fvgs = KeyZoneEngine.detect_fair_value_gaps(candles)
        state.active_keyzones = obs + fvgs

        # 3. Detect Liquidity Pools (EQH/EQL) & Active Sweeps
        pools = LiquidityEngine.detect_equal_levels(state.active_swings)
        sweeps = LiquidityEngine.detect_sweeps(candles, pools)

        # 4. Attach Mapped Liquidity to Payload
        state.active_liquidity_pools = pools
        state.active_liquidity_sweeps = sweeps

        return state
