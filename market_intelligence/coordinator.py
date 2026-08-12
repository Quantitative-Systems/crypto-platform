"""
APEX Quantitative Systems Platform
Product 01 — Market Language | Engine 9 — Language Coordinator

PURPOSE
-------
Orchestrates the sequential execution of Engines 1-8.
Manages the in-memory ring array, error isolation, and 
returns the final MarketStatePayload.

SEMANTIC CONTRACT
-----------------
1. Pure orchestration. No logic generation.
2. Isolates exceptions inside the pipeline.
3. HTF -> MTF -> LTF cascading (to be expanded).
"""

from typing import List, Optional

from market_intelligence.primitives import Candle, MarketStatePayload
from market_intelligence.raw_swing_engine import RawSwingEngine
from market_intelligence.structure_builder_engine import StructureBuilderEngine
from market_intelligence.liquidity_engine import LiquidityEngine
from market_intelligence.keyzone_engine import KeyZoneEngine
from market_intelligence.phase_engine import PhaseEngine
from market_intelligence.trend_engine import TrendEngine
from market_intelligence.validation_engine import ValidationEngine
from market_intelligence.market_state import MarketStateAggregator


class CoordinatorError(Exception):
    pass


class LanguageCoordinator:
    """
    Coordinates the execution of all market intelligence engines.
    """

    def __init__(self, buffer_size: int = 500):
        self.buffer_size = buffer_size
        
        self.raw_swing_engine = RawSwingEngine()
        self.structure_engine = StructureBuilderEngine()
        self.liquidity_engine = LiquidityEngine()
        self.keyzone_engine = KeyZoneEngine()
        self.phase_engine = PhaseEngine()
        self.trend_engine = TrendEngine()
        self.validation_engine = ValidationEngine()
        self.aggregator = MarketStateAggregator()

    def run(self, candles: List[Candle], symbol: str = "BTCUSD", timeframe: str = "1H") -> MarketStatePayload:
        if not candles:
            # We could return an empty payload, but per spec raising or erroring on empty is safer.
            raise CoordinatorError("Empty candle list provided to coordinator.")
            
        if len(candles) > self.buffer_size:
            candles = candles[-self.buffer_size:]

        try:
            # Engine 1
            swings = self.raw_swing_engine.detect(candles)

            # Engine 2
            structure_state = self.structure_engine.process(swings, candles)

            # Engine 3
            liquidity_state = self.liquidity_engine.process(
                structure_state.sequence_swings, candles, structure_state.external_trend
            )

            # Engine 4
            keyzone_state = self.keyzone_engine.process(
                candles, structure_state.events, liquidity_state
            )

            # Engine 5
            phase_state = self.phase_engine.process(
                candles, structure_state.events, liquidity_state, keyzone_state
            )

            # Engine 6
            trend_state = self.trend_engine.evaluate(structure_state, phase_state)

            # Engine 7
            all_keyzones = keyzone_state.active_zones + keyzone_state.mitigated_zones
            validation_result = self.validation_engine.evaluate(
                candles, swings, structure_state, all_keyzones
            )

            # Aggregate events
            all_events = (
                structure_state.events
                + liquidity_state.events
                + keyzone_state.events
                + phase_state.events
            )

            # Engine 8
            inputs = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": candles[-1].timestamp,
                "current_price": candles[-1].close,
                "current_candle": candles[-1],
                "events": all_events,
                "swings": swings,
                "structure_state": structure_state,
                "liquidity_pools": liquidity_state.active_pools,
                "keyzones": all_keyzones,
                "phase_state": phase_state.current_phase,
                "trend_state": trend_state.direction,
                "valuation_state": "EQUILIBRIUM",
                "scorecard": {
                    "validation_score": validation_result.score,
                    "reason_codes": validation_result.reason_codes,
                    "validation_status": validation_result.status.value,
                },
                "metadata": {
                    "trend_health": trend_state.health.value,
                    "causal_evidence": trend_state.causal_evidence,
                },
            }

            return self.aggregator.aggregate(inputs)

        except Exception as e:
            raise CoordinatorError(f"Pipeline execution failed: {str(e)}") from e
