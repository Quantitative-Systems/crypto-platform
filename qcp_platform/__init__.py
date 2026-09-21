"""QCP Platform — all-horizon, all-asset, cost-aware, self-improving trading platform.

Horizon ladder (one book, many clocks):
    SCALP     15m/5m/1m     seconds-minutes     (data + cost gated)
    INTRADAY  4h/1h/15m     hours               (cost gated)
    SWING     1d/4h/1h      days                (proven zone)
    POSITION  1w/1d/4h      weeks-months        (proven zone)
    INVEST    1M/1w/1d      months-years        (proven zone)
    CARRY     8h funding     weeks-months        (market-neutral)

Design rules (non-negotiable):
 1. Causality: every signal at bar i uses only data with close_ts <= close_ts(i).
 2. Costs always on: taker/maker fees + slippage + spread (+ basis for carry).
 3. Out-of-sample is never tuned. Walk-forward only.
 4. Risk first: no single position, strategy, or asset may threaten the account.
 5. Refusal is a valid output: a horizon that cannot pay its costs is reported
    NOT_ECONOMIC rather than force-fit with fabricated edge.
"""
from __future__ import annotations

__all__ = [
    "costs", "indicators", "data", "regimes", "horizons",
    "strategies", "engine", "governor", "walkforward",
    "evaluate", "runner",
]

__version__ = "1.0.0"
