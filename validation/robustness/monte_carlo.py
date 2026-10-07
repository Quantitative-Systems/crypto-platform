"""Monte Carlo Robustness & Sequence Risk Simulation Engine.

Evaluates trading strategy trade logs under non-parametric stress tests:
1. Trade Order Shuffling (Sequence Risk & Worst-Case Drawdown)
2. Trade Dropout Sampling (Outlier Dependency & Luck Factor)
3. Friction Jitter Stress (Slippage & Fee Shock Resilience)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np


@dataclass
class MonteCarloReport:
    """Summary of Monte Carlo stress testing."""
    original_trade_count: int
    original_total_r: float
    original_max_dd_r: float
    p95_max_dd_r: float
    p50_max_dd_r: float
    p05_max_dd_r: float
    dropout_positive_expectancy_rate: float
    friction_stressed_expectancy_r: float
    is_monte_carlo_pass: bool
    ruin_probability: float
    summary: Dict[str, Any]


class MonteCarloSimulator:
    """Institutional Monte Carlo simulation harness."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)

    def evaluate_candidate(
        self,
        realized_r_list: List[float],
        n_shuffles: int = 1000,
        dropout_rate: float = 0.20,
        friction_shock_r: float = 0.08,
    ) -> MonteCarloReport:
        """Run complete battery of Monte Carlo stress tests on trade logs."""
        trades = np.array(realized_r_list, dtype=np.float64)
        n = len(trades)
        if n < 5:
            return MonteCarloReport(
                original_trade_count=n,
                original_total_r=float(np.sum(trades)),
                original_max_dd_r=0.0,
                p95_max_dd_r=99.0,
                p50_max_dd_r=99.0,
                p05_max_dd_r=99.0,
                dropout_positive_expectancy_rate=0.0,
                friction_stressed_expectancy_r=-99.0,
                is_monte_carlo_pass=False,
                ruin_probability=1.0,
                summary={"reason": "INSUFFICIENT_TRADES"},
            )

        orig_total_r = float(np.sum(trades))
        orig_max_dd = self._calc_max_dd(trades)

        # 1. Trade Order Shuffling (Sequence Risk)
        shuffle_dds = []
        ruin_count = 0
        ruin_threshold_r = 25.0  # Max acceptable drawdown in R units

        for _ in range(n_shuffles):
            shuffled = self.rng.permutation(trades)
            dd = self._calc_max_dd(shuffled)
            shuffle_dds.append(dd)
            if dd >= ruin_threshold_r:
                ruin_count += 1

        p95_dd = float(np.percentile(shuffle_dds, 95))
        p50_dd = float(np.percentile(shuffle_dds, 50))
        p05_dd = float(np.percentile(shuffle_dds, 5))
        ruin_prob = float(ruin_count / n_shuffles)

        # 2. Trade Dropout Sampling (20% random drop)
        n_keep = max(3, int(n * (1.0 - dropout_rate)))
        dropout_pos_count = 0
        n_dropout_sims = 500

        for _ in range(n_dropout_sims):
            sample_idx = self.rng.choice(n, size=n_keep, replace=False)
            sub_sample = trades[sample_idx]
            if np.mean(sub_sample) > 0:
                dropout_pos_count += 1

        dropout_pos_rate = float(dropout_pos_count / n_dropout_sims)

        # 3. Friction Jitter Shock (-0.08R penalty per trade)
        stressed_trades = trades - friction_shock_r
        stressed_exp_r = float(np.mean(stressed_trades))

        # Qualification Gate:
        # 1. p95 Max DD < 20R
        # 2. Dropout positive expectancy rate > 80%
        # 3. Friction stressed expectancy > 0
        is_pass = (p95_dd < ruin_threshold_r) and (dropout_pos_rate >= 0.80) and (stressed_exp_r > 0)

        return MonteCarloReport(
            original_trade_count=n,
            original_total_r=round(orig_total_r, 2),
            original_max_dd_r=round(orig_max_dd, 2),
            p95_max_dd_r=round(p95_dd, 2),
            p50_max_dd_r=round(p50_dd, 2),
            p05_max_dd_r=round(p05_dd, 2),
            dropout_positive_expectancy_rate=round(dropout_pos_rate, 4),
            friction_stressed_expectancy_r=round(stressed_exp_r, 4),
            is_monte_carlo_pass=bool(is_pass),
            ruin_probability=round(ruin_prob, 4),
            summary={
                "n_shuffles": n_shuffles,
                "n_dropout_sims": n_dropout_sims,
                "dropout_rate": dropout_rate,
                "friction_shock_r": friction_shock_r,
            },
        )

    def _calc_max_dd(self, r_series: np.ndarray) -> float:
        equity = np.cumsum(r_series)
        peaks = np.maximum.accumulate(equity)
        drawdowns = peaks - equity
        return float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
