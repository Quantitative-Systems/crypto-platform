"""Crypto Engine — Production-Certified Autonomous Quantitative Trading System.

This package contains EXCLUSIVELY filter-passed, empirically validated production assets.
All unvalidated research, exploratory experiments, and failed models reside outside
in the `research/` directory.

Architecture:
- `core/`: Scale-invariant 3-pillar market model & cascading multi-horizon coordinator.
- `execution/`: 24/7/365 live execution engine, autonomous daemon, and broker adapters.
- `risk/`: Capital preservation, dynamic 1% risk sizing, and circuit breakers.
- `pipeline/`: Automated Promotion Gate separating passed vs. failed research models.
- `registry/`: Certified production champions active in live/demo trading.
- `alerts/`: Multi-channel operational notification router.
"""
__version__ = "2.0.0"
