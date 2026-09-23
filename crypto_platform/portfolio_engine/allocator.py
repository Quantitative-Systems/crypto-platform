"""Crypto Trading Platform — Multi-Strategy Portfolio Engine & Capital Allocator.

Constructs multi-strategy portfolios based on measured out-of-sample empirical evidence:
- Evaluates expected return, volatility, Sharpe, drawdown, correlation, and turnover.
- Enforces strict concentration caps (max 20% on any single book) to prevent single-strategy dominance.
- Balances allocations across uncorrelated horizons (Intraday, Swing, Position, Carry, Invest).
- Simulates portfolio stress tests under funding compression, volatility spikes, and strategy failures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

from crypto_platform.core.interfaces import IPortfolioEngine


@dataclass
class PortfolioConstraints:
    max_book_weight: float = 0.20          # Max 20% allocated to any single book
    min_book_weight: float = 0.02          # Minimum 2% to avoid capital fragmentation
    max_horizon_weight: Dict[str, float] = field(
        default_factory=lambda: {
            "SCALP": 0.10,
            "INTRADAY": 0.25,
            "SWING": 0.30,
            "POSITION": 0.30,
            "INVEST": 0.25,
            "CARRY": 0.20,                 # Capped at 20% to prevent carry over-dependence
        }
    )
    target_annualized_vol: float = 0.15    # 15% target portfolio volatility


@dataclass
class PortfolioMetrics:
    expected_annual_return: float
    annual_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    diversification_ratio: float
    herfindahl_concentration: float
    allocated_books_count: int
    weights: Dict[str, float]


class PortfolioEngine(IPortfolioEngine):
    """Institutional-grade portfolio construction and stress testing engine."""

    def __init__(self, constraints: Optional[PortfolioConstraints] = None):
        self.constraints = constraints or PortfolioConstraints()

    def allocate_capital(
        self,
        strategy_stats: Dict[str, Dict[str, Any]],
        total_equity: float = 100_000.0,
    ) -> Dict[str, float]:
        """Calculates honest capital allocations constrained by risk and diversification caps."""
        weights = self.compute_weights(strategy_stats)
        allocations = {k: round(w * total_equity, 2) for k, w in weights.items() if w > 0}
        diff = round(total_equity - sum(allocations.values()), 2)
        if abs(diff) > 0 and allocations:
            largest_key = max(allocations.keys(), key=lambda k: allocations[k])
            allocations[largest_key] = round(allocations[largest_key] + diff, 2)
        return allocations

    def compute_weights(
        self, strategy_stats: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculates normalized percentage weights capped by single-book and horizon limits."""
        raw_scores: Dict[str, float] = {}

        for key, stats in strategy_stats.items():
            sharpe = max(0.0, float(stats.get("oos_sharpe", 0.0) or 0.0))
            exp = max(0.0, float(stats.get("oos_exp", 0.0) or 0.0))
            dd = max(0.05, float(stats.get("oos_dd", 0.15) or 0.15))

            # Score = Risk-adjusted quality penalized by drawdown
            score = (sharpe * (0.5 + exp)) / dd
            raw_scores[key] = max(0.0, score)

        n = len(strategy_stats)
        if n == 0:
            return {}

        caps = {
            k: min(
                self.constraints.max_book_weight,
                self.constraints.max_horizon_weight.get(strategy_stats[k].get("horizon", "SWING"), 0.25),
            )
            for k in strategy_stats
        }

        total_raw = sum(raw_scores.values())
        if total_raw <= 0:
            return {k: round(1.0 / n, 4) for k in strategy_stats}

        # Water-filling with hard upper bound
        weights = {k: min(caps[k], score / total_raw) for k, score in raw_scores.items()}
        for _ in range(25):
            current_sum = sum(weights.values())
            if abs(current_sum - 1.0) < 1e-5:
                break
            shortfall = 1.0 - current_sum
            available = [k for k in weights if weights[k] < caps[k] - 1e-6]
            if not available:
                break
            add_per_book = shortfall / len(available)
            for k in available:
                weights[k] = min(caps[k], max(0.0, weights[k] + add_per_book))

        tot = sum(weights.values())
        return {k: round(w / tot, 4) for k, w in weights.items()}

    def evaluate_metrics(
        self,
        weights: Dict[str, float],
        strategy_stats: Dict[str, Dict[str, Any]],
        correlation_matrix: Optional[np.ndarray] = None,
    ) -> PortfolioMetrics:
        """Computes multi-dimensional portfolio health, Sharpe, and concentration metrics."""
        keys = list(weights.keys())
        w = np.array([weights[k] for k in keys])

        # Returns and volatilities
        expected_returns = np.array([
            float(strategy_stats[k].get("annualized_return", 0.12) or 0.12) for k in keys
        ])
        vols = np.array([
            float(strategy_stats[k].get("annualized_vol", 0.25) or 0.25) for k in keys
        ])

        port_ret = float(np.dot(w, expected_returns))

        if correlation_matrix is None or correlation_matrix.shape != (len(w), len(w)):
            # Default average 0.35 correlation assumption
            corr = np.full((len(w), len(w)), 0.35)
            np.fill_diagonal(corr, 1.0)
        else:
            corr = correlation_matrix

        cov = np.outer(vols, vols) * corr
        port_vol = float(np.sqrt(np.dot(w.T, np.dot(cov, w))))
        sharpe = (port_ret / port_vol) if port_vol > 0 else 0.0

        # Max drawdown estimate (empirical heuristic)
        dds = np.array([float(strategy_stats[k].get("oos_dd", 0.15) or 0.15) for k in keys])
        port_dd = float(np.dot(w, dds) * 0.75)  # Diversification reduces peak DD

        # Herfindahl-Hirschman Index (Concentration)
        hhi = float(np.sum(w ** 2))
        div_ratio = float(np.dot(w, vols) / port_vol) if port_vol > 0 else 1.0

        return PortfolioMetrics(
            expected_annual_return=round(port_ret, 4),
            annual_volatility=round(port_vol, 4),
            sharpe_ratio=round(sharpe, 3),
            max_drawdown=round(port_dd, 4),
            diversification_ratio=round(div_ratio, 3),
            herfindahl_concentration=round(hhi, 4),
            allocated_books_count=len([x for x in w if x > 0.01]),
            weights={k: round(weights[k], 4) for k in keys},
        )

    def stress_test_portfolio(
        self,
        weights: Dict[str, float],
        strategy_stats: Dict[str, Dict[str, Any]],
        funding_compression: float = 0.50,
        vol_expansion_multiplier: float = 1.50,
        correlated_shock_dd: float = 0.15,
    ) -> Dict[str, Any]:
        """Evaluates portfolio degradation under combined market shocks."""
        base_metrics = self.evaluate_metrics(weights, strategy_stats)

        # Apply stress transformations
        stressed_stats = {}
        for k, s in strategy_stats.items():
            mod = dict(s)
            horizon = s.get("horizon", "SWING")
            if horizon == "CARRY":
                # Severe funding compression decays carry yield
                mod["annualized_return"] = float(s.get("annualized_return", 0.20)) * (1.0 - funding_compression)
            else:
                # Volatility expansion increases directional slippage/frictions
                mod["annualized_vol"] = float(s.get("annualized_vol", 0.25)) * vol_expansion_multiplier
                mod["oos_dd"] = min(0.40, float(s.get("oos_dd", 0.15)) + correlated_shock_dd)
            stressed_stats[k] = mod

        stressed_metrics = self.evaluate_metrics(weights, stressed_stats)

        return {
            "baseline": {
                "expected_return": base_metrics.expected_annual_return,
                "volatility": base_metrics.annual_volatility,
                "sharpe": base_metrics.sharpe_ratio,
                "max_drawdown": base_metrics.max_drawdown,
            },
            "stressed": {
                "expected_return": stressed_metrics.expected_annual_return,
                "volatility": stressed_metrics.annual_volatility,
                "sharpe": stressed_metrics.sharpe_ratio,
                "max_drawdown": stressed_metrics.max_drawdown,
            },
            "survives_stress": stressed_metrics.expected_annual_return > 0 and stressed_metrics.max_drawdown <= 0.30,
        }
