"""Phase L: Stress Testing & Independent Robustness Harness.

Executes the 7 independent stress tests attacking the frozen candidate:
L1 - Cost Stress (1x to 5x friction degradation)
L2 - Parameter Perturbation (Fragility & Plateau Stability Index)
L3 - Asset Transfer (Leave-one-asset-out cross-validation)
L4 - Timeframe Transfer (Alternate MTF triplet sets)
L5 - Monte Carlo Resampling (Sequence risk, ruin probability, recovery time)
L6 - Crisis Blind Test (Pre-defined unseen crisis & stress episodes)
L7 - Reactivation Isolation Test (Resolving System 2 vs System 3 incremental value)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from execution.backtest.engine import TradeRecord
from validation.robustness.contracts import (
    AssetTransferResult,
    CostStressResult,
    CrisisBlindEpisodeResult,
    MonteCarloResampleResult,
    ParameterPerturbationResult,
    ReactivationIsolationResult,
    TimeframeTransferResult,
)
from validation.robustness.monte_carlo import MonteCarloSimulator
from validation.robustness.parameter_stability import ParameterStabilityAnalyzer


class RobustnessStressTester:
    """Institutional stress test engine attacking the frozen candidate."""

    def __init__(self, rng_seed: int = 42):
        self.rng = np.random.default_rng(rng_seed)
        self.mc_sim = MonteCarloSimulator(seed=rng_seed)
        self.stability_analyzer = ParameterStabilityAnalyzer()

    def run_cost_stress_test(
        self,
        trades: List[TradeRecord],
        base_friction_r: float = 0.06,
        multipliers: Optional[List[float]] = None,
    ) -> List[CostStressResult]:
        """L1: Evaluate degradation under 1x to 5x friction shocks."""
        if multipliers is None:
            multipliers = [1.0, 2.0, 3.0, 4.0, 5.0]

        results: List[CostStressResult] = []
        raw_r = np.array([t.realized_r for t in trades], dtype=np.float64)
        n = len(raw_r)

        for mult in multipliers:
            added_penalty_per_trade = (mult - 1.0) * base_friction_r
            stressed_r = raw_r - added_penalty_per_trade
            net_r = float(np.sum(stressed_r)) if n > 0 else 0.0
            exp_r = float(np.mean(stressed_r)) if n > 0 else 0.0

            wins = stressed_r[stressed_r > 0]
            losses = stressed_r[stressed_r < 0]
            win_rate = float(len(wins) / n * 100.0) if n > 0 else 0.0

            gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
            gross_loss = float(abs(np.sum(losses))) if len(losses) > 0 else 1e-6
            pf = gross_profit / gross_loss

            # Drawdown
            equity = np.cumsum(stressed_r)
            peaks = np.maximum.accumulate(equity)
            dd = peaks - equity
            max_dd_r = float(np.max(dd)) if len(dd) > 0 else 0.0
            # Approx % max DD (1R = 1.0% equity)
            max_dd_pct = max_dd_r * 1.0

            results.append(
                CostStressResult(
                    multiplier=mult,
                    effective_friction_per_trade_r=round(mult * base_friction_r, 3),
                    trade_count=n,
                    net_r=round(net_r, 2),
                    expectancy_r=round(exp_r, 3),
                    win_rate=round(win_rate, 1),
                    profit_factor=round(pf, 2),
                    max_drawdown_pct=round(max_dd_pct, 2),
                    is_positive_expectancy=(exp_r > 0),
                )
            )

        return results

    def run_parameter_perturbation(
        self,
        parameter_name: str,
        baseline_val: float,
        test_values: List[float],
        trades_by_param: Dict[float, List[TradeRecord]],
    ) -> ParameterPerturbationResult:
        """L2: Quantify performance sensitivity and plateau stability index."""
        exp_rs: List[float] = []
        net_rs: List[float] = []
        max_dds: List[float] = []

        for p in test_values:
            t_list = trades_by_param.get(p, [])
            if t_list:
                r_arr = np.array([t.realized_r for t in t_list], dtype=np.float64)
                exp_rs.append(float(np.mean(r_arr)))
                net_rs.append(float(np.sum(r_arr)))
                equity = np.cumsum(r_arr)
                peaks = np.maximum.accumulate(equity)
                dd = peaks - equity
                max_dds.append(float(np.max(dd)) if len(dd) > 0 else 0.0)
            else:
                exp_rs.append(0.0)
                net_rs.append(0.0)
                max_dds.append(0.0)

        stab_report = self.stability_analyzer.evaluate_1d_stability(
            parameter_name=parameter_name,
            param_values=test_values,
            expectancy_r_values=exp_rs,
            plateau_threshold_psi=0.60,
        )

        is_fragile = not stab_report.is_stable_plateau
        summary_msg = (
            f"Parameter '{parameter_name}' exhibits robust plateau (PSI={stab_report.plateau_stability_index:.2f})"
            if not is_fragile
            else f"Parameter '{parameter_name}' exhibits fragility/cliff-edge (PSI={stab_report.plateau_stability_index:.2f})"
        )

        return ParameterPerturbationResult(
            parameter_name=parameter_name,
            baseline_value=baseline_val,
            tested_values=test_values,
            expectancies_r=[round(x, 3) for x in exp_rs],
            net_rs=[round(x, 2) for x in net_rs],
            max_drawdowns_pct=[round(x, 2) for x in max_dds],
            plateau_stability_index=stab_report.plateau_stability_index,
            is_fragile=is_fragile,
            summary=summary_msg,
        )

    def run_monte_carlo_resampling(
        self,
        trades: List[TradeRecord],
        n_iterations: int = 2000,
        ruin_threshold_r: float = 25.0,
    ) -> MonteCarloResampleResult:
        """L5: Sequence shuffling, drawdown distribution, and dropout sensitivity."""
        r_list = [t.realized_r for t in trades]
        r_arr = np.array(r_list, dtype=np.float64)
        n = len(r_arr)
        orig_net_r = float(np.sum(r_arr)) if n > 0 else 0.0

        # Calc original max dd
        orig_equity = np.cumsum(r_arr)
        orig_peaks = np.maximum.accumulate(orig_equity)
        orig_dd = orig_peaks - orig_equity
        orig_max_dd_r = float(np.max(orig_dd)) if len(orig_dd) > 0 else 0.0

        # 1. Resample order (Sequence risk)
        final_rs = []
        max_dds = []
        ruins = 0
        losing_streaks = []
        recovery_durations = []

        for _ in range(n_iterations):
            perm = self.rng.permutation(r_arr)
            eq = np.cumsum(perm)
            peaks = np.maximum.accumulate(eq)
            dd = peaks - eq
            max_d = float(np.max(dd)) if len(dd) > 0 else 0.0
            max_dds.append(max_d)
            final_rs.append(float(eq[-1]))
            if max_d >= ruin_threshold_r:
                ruins += 1

            # Longest losing streak
            curr_streak = 0
            max_streak = 0
            for r in perm:
                if r < 0:
                    curr_streak += 1
                    if curr_streak > max_streak:
                        max_streak = curr_streak
                else:
                    curr_streak = 0
            losing_streaks.append(max_streak)

            # Recovery duration (trades to new equity high after peak drawdown)
            peak_idx = int(np.argmax(dd)) if len(dd) > 0 else 0
            recov = len(perm) - peak_idx
            recovery_durations.append(recov)

        p05_net_r = float(np.percentile(final_rs, 5))
        p50_net_r = float(np.percentile(final_rs, 50))
        p95_net_r = float(np.percentile(final_rs, 95))
        p95_max_dd_r = float(np.percentile(max_dds, 95))
        ruin_prob = float(ruins / n_iterations)
        streak_p95 = int(np.percentile(losing_streaks, 95))
        avg_recov = float(np.mean(recovery_durations))

        # CVaR 95% on single-trade outcomes
        var95 = float(np.percentile(r_arr, 5))
        tail = r_arr[r_arr <= var95]
        cvar95 = float(np.mean(tail)) if len(tail) > 0 else var95

        # 20% trade dropout
        dropout_report = self.mc_sim.evaluate_candidate(r_list, n_shuffles=500, dropout_rate=0.20)
        dropout_pos_rate = dropout_report.dropout_positive_expectancy_rate

        is_resilient = (ruin_prob == 0.0) and (p95_max_dd_r < ruin_threshold_r) and (dropout_pos_rate >= 0.80)

        return MonteCarloResampleResult(
            iterations=n_iterations,
            original_trade_count=n,
            original_net_r=round(orig_net_r, 2),
            p05_net_r=round(p05_net_r, 2),
            p50_net_r=round(p50_net_r, 2),
            p95_net_r=round(p95_net_r, 2),
            original_max_dd_r=round(orig_max_dd_r, 2),
            p95_max_dd_r=round(p95_max_dd_r, 2),
            ruin_probability=round(ruin_prob, 4),
            cvar_95_r=round(cvar95, 2),
            longest_losing_streak_p95=streak_p95,
            avg_recovery_trades=round(avg_recov, 1),
            dropout_positive_rate=round(dropout_pos_rate * 100.0, 1),
            is_resilient=is_resilient,
        )
