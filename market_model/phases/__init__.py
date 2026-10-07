"""Market Phases Package.

Exposes causal phase detection engines:
- Phase identification (ACCUMULATION, TREND_EXPANSION, PULLBACK, EXHAUSTION, DISTRIBUTION)
- Pullback depth, speed, and volume characteristics
- Continuation momentum and expansion quality metrics
"""
from market_model.phases.pullback.detection.phase_engine import PhaseEngine

__all__ = ["PhaseEngine"]
