"""
Quantitative Crypto Platform (QCP) — Relative Value Research Configuration.

Defines canonical research configurations, pair universes, econometric thresholds,
and decomposed execution friction models for cross-asset statistical arbitrage.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any


@dataclass
class DecomposedFrictionModel:
    """
    Explicitly decomposed transaction friction across two legs (A and B).
    """
    taker_fee_bps_per_leg: float = 5.0          # 5 bps taker fee on Binance VIP 0
    slippage_bps_per_leg: float = 3.0           # 3 bps spread crossing + market impact
    borrow_apr_pct: float = 6.0                 # Financing cost if margin borrowed
    holding_cost_annual_pct: float = 1.0        # Opportunity / carry cost

    @property
    def single_leg_roundtrip_bps(self) -> float:
        # (entry fee + entry slip) + (exit fee + exit slip)
        return (self.taker_fee_bps_per_leg + self.slippage_bps_per_leg) * 2.0

    @property
    def total_pair_roundtrip_bps(self) -> float:
        # Two legs: Asset A + Asset B
        return self.single_leg_roundtrip_bps * 2.0

    @property
    def total_pair_roundtrip_pct(self) -> float:
        return self.total_pair_roundtrip_bps / 10000.0


@dataclass
class RelativeValueConfig:
    """
    Central research configuration for Family 09 Relative Value.
    """
    # Universe pairs: (Symbol A, Symbol B, Canonical Pair Name)
    # Using USDT as common pricing currency
    pairs: List[Tuple[str, str, str]] = field(default_factory=lambda: [
        ("BTC/USDT", "ETH/USDT", "BTC/ETH"),
        ("SOL/USDT", "ETH/USDT", "SOL/ETH"),
        ("SOL/USDT", "BTC/USDT", "SOL/BTC"),
    ])

    timeframes: List[str] = field(default_factory=lambda: ["1d", "4h"])

    # Econometric Parameters
    rolling_lookback_window: int = 60          # 60 bars for causal rolling OLS & z-scores
    min_cointegration_obs: int = 120           # Minimum bars required for Engle-Granger / Johansen
    cointegration_pvalue_threshold: float = 0.05  # 5% significance hurdle for cointegration
    max_half_life_bars: float = 45.0           # Configurable heuristic: reject if half-life > 45 bars

    # Trading Signal Parameters
    entry_z_threshold: float = 2.0             # Entry when |z| >= 2.0
    exit_z_threshold: float = 0.2              # Mean-reversion exit when |z| <= 0.2
    stop_loss_z: float = 3.5                   # Invalidation / divergence stop when |z| >= 3.5
    max_holding_bars: int = 45                 # Time-expiry exit (45 bars)
    risk_unit_spread_pct: float = 0.05         # 1R normalized to 5% spread move

    # Chronological Evidence Partitions
    dev_start_ts: int = 1597449600             # 2020-08-15 00:00:00 UTC
    dev_end_ts: int = 1672531199               # 2022-12-31 23:59:59 UTC
    val_start_ts: int = 1672531200             # 2023-01-01 00:00:00 UTC
    val_end_ts: int = 1704067199               # 2023-12-31 23:59:59 UTC
    oos_start_ts: int = 1704067200             # 2024-01-01 00:00:00 UTC
    oos_end_ts: int = 1788220800               # 2026-09-01 00:00:00 UTC

    # Friction Model
    friction: DecomposedFrictionModel = field(default_factory=DecomposedFrictionModel)

    def get_stress_friction(self, multiplier: float = 2.0) -> DecomposedFrictionModel:
        """Returns stressed friction model (e.g. 2x friction = 64 bps total roundtrip)."""
        return DecomposedFrictionModel(
            taker_fee_bps_per_leg=self.friction.taker_fee_bps_per_leg * multiplier,
            slippage_bps_per_leg=self.friction.slippage_bps_per_leg * multiplier,
            borrow_apr_pct=self.friction.borrow_apr_pct,
            holding_cost_annual_pct=self.friction.holding_cost_annual_pct,
        )
