"""Strategy Hypotheses Package.

All strategy hypotheses are decoupled from the core Market Model.
Each hypothesis strictly decomposes its logic across the 3 canonical dimensions:
1. MARKET STRUCTURE / TREND
2. KEY ZONES / LEVELS
3. PHASE

Available Hypotheses:
- BaselineStrategyHypothesisV1: Canonical baseline (Pullback & Continuation with OB/FVG/BOS)
- TrendBreakoutHypothesis: HTF trend breakout through dealing range S/R boundaries
- MeanReversionHypothesis: Range consolidation reversal from Premium/Discount to Equilibrium
- MomentumIgnitionHypothesis: Compression squeeze explosion into expansion
"""
from strategy.base import CandidateSignal, StrategyHypothesis
from strategy.baseline_v1 import BaselineStrategyHypothesisV1
from strategy.trend_breakout import TrendBreakoutHypothesis
from strategy.mean_reversion import MeanReversionHypothesis
from strategy.momentum_ignition import MomentumIgnitionHypothesis
from strategy.adaptive.adaptive_causal_engine import AdaptiveCausalEngine
from strategy.adaptive.adaptive_engine_v1 import AdaptiveEngineV1

__all__ = [
    "CandidateSignal",
    "StrategyHypothesis",
    "BaselineStrategyHypothesisV1",
    "TrendBreakoutHypothesis",
    "MeanReversionHypothesis",
    "MomentumIgnitionHypothesis",
    "AdaptiveCausalEngine",
    "AdaptiveEngineV1",
]
