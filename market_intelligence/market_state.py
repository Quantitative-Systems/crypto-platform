"""
APEX Quantitative Systems Platform
Product 01 — Market Language | Engine 8 — Market State Aggregator

PURPOSE
-------
Pure aggregation layer to unify outputs from Engines 1-7 into a single,
immutable MarketStatePayload.

SEMANTIC CONTRACT
-----------------
1. No computation of new market concepts (no swings, no phases).
2. Standardizes schema for downstream serialization.
"""

from typing import Dict, Any
from market_intelligence.primitives import MarketStatePayload


class MarketStateAggregator:
    """
    Aggregates engine outputs into the final MarketStatePayload.
    """

    def aggregate(self, inputs: Dict[str, Any]) -> MarketStatePayload:
        required_keys = [
            "symbol",
            "timeframe",
            "timestamp",
            "current_price",
            "current_candle",
            "events",
            "swings",
            "structure_state",
            "liquidity_pools",
            "keyzones",
        ]

        for key in required_keys:
            if key not in inputs:
                raise ValueError(f"Missing required input for aggregation: {key}")

        return MarketStatePayload(
            symbol=inputs["symbol"],
            timeframe=inputs["timeframe"],
            timestamp=inputs["timestamp"],
            current_price=inputs["current_price"],
            current_candle=inputs["current_candle"],
            events=inputs["events"],
            swings=inputs["swings"],
            structure_state=inputs["structure_state"],
            liquidity_pools=inputs["liquidity_pools"],
            keyzones=inputs["keyzones"],
            phase_state=inputs.get("phase_state"),
            trend_state=inputs.get("trend_state"),
            valuation_state=inputs.get("valuation_state", "EQUILIBRIUM"),
            scorecard=inputs.get("scorecard"),
            metadata=inputs.get("metadata"),
        )
