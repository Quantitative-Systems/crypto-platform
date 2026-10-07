"""
Quantitative Crypto Platform (QCP) — Independent Performance Truth Engine.

Provides mathematically rigorous, independent reconciliation of trading performance,
equity trajectories, drawdowns, risk-adjusted metrics, and tail-loss distributions.
Eliminates reporting discrepancies and prevents unverified metrics (e.g. 0% drawdown)
from masquerading as institutional validation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple
import math
import numpy as np


@dataclass
class DrawdownMetrics:
    max_drawdown_usd: float
    max_drawdown_pct: float
    peak_equity_usd: float
    trough_equity_usd: float
    avg_drawdown_pct: float
    max_drawdown_duration_trades: int
    current_drawdown_pct: float


@dataclass
class RiskAdjustedMetrics:
    annualized_return_pct: float
    annualized_volatility_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    return_over_max_dd: float


@dataclass
class TailRiskMetrics:
    var_95_usd: float
    cvar_95_usd: float
    var_95_r: float
    cvar_95_r: float
    worst_trade_loss_usd: float
    worst_trade_loss_r: float
    max_consecutive_losses: int
    max_consecutive_wins: int


@dataclass
class FrictionMetrics:
    total_entry_fee_usd: float
    total_exit_fee_usd: float
    total_slippage_usd: float
    total_friction_usd: float
    avg_friction_r: float
    friction_drag_pct: float


@dataclass
class ComprehensivePerformanceAudit:
    starting_capital_usd: float
    ending_equity_usd: float
    net_profit_usd: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    gross_profit_usd: float
    gross_loss_usd: float
    avg_win_usd: float
    avg_loss_usd: float
    payoff_ratio: float
    total_net_r: float
    expectancy_r: float
    profit_factor_r: float
    std_dev_r: float
    drawdown: DrawdownMetrics
    risk_adjusted: RiskAdjustedMetrics
    tail_risk: TailRiskMetrics
    friction: FrictionMetrics

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PerformanceTruthEngine:
    """
    Independent Performance Truth Engine for QCP.
    Audits execution records and recalculates all metrics from scratch.
    """

    @classmethod
    def audit_trades(
        cls,
        trades: List[Dict[str, Any]],
        starting_capital: float = 1000.0,
        annualization_periods: int = 365 * 6,  # 4H candles per year (2,190 bars)
    ) -> ComprehensivePerformanceAudit:
        """
        Performs full independent forensic audit over a sequence of completed trades.
        """
        n = len(trades)
        if n == 0:
            empty_dd = DrawdownMetrics(0.0, 0.0, starting_capital, starting_capital, 0.0, 0, 0.0)
            empty_risk = RiskAdjustedMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            empty_tail = TailRiskMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)
            empty_fric = FrictionMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            return ComprehensivePerformanceAudit(
                starting_capital_usd=starting_capital,
                ending_equity_usd=starting_capital,
                net_profit_usd=0.0,
                total_return_pct=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                gross_profit_usd=0.0,
                gross_loss_usd=0.0,
                avg_win_usd=0.0,
                avg_loss_usd=0.0,
                payoff_ratio=0.0,
                total_net_r=0.0,
                expectancy_r=0.0,
                profit_factor_r=0.0,
                std_dev_r=0.0,
                drawdown=empty_dd,
                risk_adjusted=empty_risk,
                tail_risk=empty_tail,
                friction=empty_fric,
            )

        # 1. Equity Curve and Running Drawdown
        equity = starting_capital
        equity_curve = [equity]
        peak = starting_capital
        max_dd_usd = 0.0
        max_dd_pct = 0.0
        drawdown_pcts = []
        trough_at_max_dd = starting_capital
        peak_at_max_dd = starting_capital

        current_dd_duration = 0
        max_dd_duration = 0

        for t in trades:
            net_pnl = float(t.get("net_pnl_usd", 0.0))
            equity += net_pnl
            equity_curve.append(equity)

            if equity > peak:
                peak = equity
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                if current_dd_duration > max_dd_duration:
                    max_dd_duration = current_dd_duration

            dd_usd = peak - equity
            dd_pct = (dd_usd / peak) * 100.0 if peak > 0 else 0.0
            drawdown_pcts.append(dd_pct)

            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
                trough_at_max_dd = equity
                peak_at_max_dd = peak

            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        current_dd_pct = ((peak - equity) / peak * 100.0) if peak > 0 else 0.0
        non_zero_dds = [d for d in drawdown_pcts if d > 1e-4]
        avg_dd_pct = float(np.mean(non_zero_dds)) if non_zero_dds else 0.0

        dd_metrics = DrawdownMetrics(
            max_drawdown_usd=round(max_dd_usd, 4),
            max_drawdown_pct=round(max_dd_pct, 4),
            peak_equity_usd=round(peak_at_max_dd, 4),
            trough_equity_usd=round(trough_at_max_dd, 4),
            avg_drawdown_pct=round(avg_dd_pct, 4),
            max_drawdown_duration_trades=max_dd_duration,
            current_drawdown_pct=round(current_dd_pct, 4),
        )

        # 2. Trade Statistics
        pnls = [float(t.get("net_pnl_usd", 0.0)) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = n_wins / n

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 1e-6 else float("inf")

        avg_win = (gross_profit / n_wins) if n_wins > 0 else 0.0
        avg_loss = (gross_loss / n_losses) if n_losses > 0 else 0.0
        payoff = (avg_win / avg_loss) if avg_loss > 1e-6 else float("inf")

        # 3. R-Accounting Distribution
        net_rs = [float(t.get("net_r", 0.0)) for t in trades]
        total_net_r = sum(net_rs)
        exp_r = total_net_r / n
        std_dev_r = float(np.std(net_rs)) if n > 1 else 0.0

        win_rs = [r for r in net_rs if r > 0]
        loss_rs = [abs(r) for r in net_rs if r < 0]
        pf_r = (sum(win_rs) / sum(loss_rs)) if sum(loss_rs) > 1e-6 else float("inf")

        # 4. Tail Risk & Loss Sequences
        worst_pnl = min(pnls) if pnls else 0.0
        worst_r = min(net_rs) if net_rs else 0.0

        max_consec_losses = 0
        curr_consec_losses = 0
        max_consec_wins = 0
        curr_consec_wins = 0

        for p in pnls:
            if p < 0:
                curr_consec_losses += 1
                curr_consec_wins = 0
                max_consec_losses = max(max_consec_losses, curr_consec_losses)
            elif p > 0:
                curr_consec_wins += 1
                curr_consec_losses = 0
                max_consec_wins = max(max_consec_wins, curr_consec_wins)
            else:
                curr_consec_losses = 0
                curr_consec_wins = 0

        var_95_usd = float(np.percentile(pnls, 5)) if pnls else 0.0
        cvar_95_losses_usd = [p for p in pnls if p <= var_95_usd]
        cvar_95_usd = float(np.mean(cvar_95_losses_usd)) if cvar_95_losses_usd else var_95_usd

        var_95_r = float(np.percentile(net_rs, 5)) if net_rs else 0.0
        cvar_95_losses_r = [r for r in net_rs if r <= var_95_r]
        cvar_95_r = float(np.mean(cvar_95_losses_r)) if cvar_95_losses_r else var_95_r

        tail_metrics = TailRiskMetrics(
            var_95_usd=round(var_95_usd, 4),
            cvar_95_usd=round(cvar_95_usd, 4),
            var_95_r=round(var_95_r, 4),
            cvar_95_r=round(cvar_95_r, 4),
            worst_trade_loss_usd=round(worst_pnl, 4),
            worst_trade_loss_r=round(worst_r, 4),
            max_consecutive_losses=max_consec_losses,
            max_consecutive_wins=max_consec_wins,
        )

        # 5. Risk-Adjusted Return Ratios
        total_pnl = equity - starting_capital
        total_ret_pct = (total_pnl / starting_capital) * 100.0

        # Trade returns as fractional portfolio gains
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            returns.append(ret)

        mean_ret = float(np.mean(returns)) if returns else 0.0
        std_ret = float(np.std(returns)) if len(returns) > 1 else 1e-6

        # Annualized scaling based on trade frequency
        annualized_return_pct = mean_ret * annualization_periods * 100.0
        annualized_vol_pct = std_ret * math.sqrt(annualization_periods) * 100.0
        sharpe = (annualized_return_pct / annualized_vol_pct) if annualized_vol_pct > 1e-6 else 0.0

        # Sortino downside semideviation
        neg_returns = [r for r in returns if r < 0]
        downside_std = float(np.std(neg_returns)) if len(neg_returns) > 1 else 1e-6
        annualized_downside_vol_pct = downside_std * math.sqrt(annualization_periods) * 100.0
        sortino = (annualized_return_pct / annualized_downside_vol_pct) if annualized_downside_vol_pct > 1e-6 else 0.0

        calmar = (annualized_return_pct / max_dd_pct) if max_dd_pct > 1e-4 else 0.0
        return_over_dd = (total_ret_pct / max_dd_pct) if max_dd_pct > 1e-4 else 0.0

        risk_adj = RiskAdjustedMetrics(
            annualized_return_pct=round(annualized_return_pct, 2),
            annualized_volatility_pct=round(annualized_vol_pct, 2),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            return_over_max_dd=round(return_over_dd, 4),
        )

        # 6. Friction Drag
        entry_fees = sum(float(t.get("entry_fee_usd", 0.0)) for t in trades)
        exit_fees = sum(float(t.get("exit_fee_usd", 0.0)) for t in trades)
        total_fric = sum(float(t.get("total_friction_usd", entry_fees + exit_fees)) for t in trades)
        avg_fric_r = float(np.mean([float(t.get("friction_r", 0.0)) for t in trades])) if trades else 0.0
        fric_drag = (total_fric / gross_profit * 100.0) if gross_profit > 1e-6 else 0.0

        fric_metrics = FrictionMetrics(
            total_entry_fee_usd=round(entry_fees, 4),
            total_exit_fee_usd=round(exit_fees, 4),
            total_slippage_usd=round(total_fric - (entry_fees + exit_fees), 4),
            total_friction_usd=round(total_fric, 4),
            avg_friction_r=round(avg_fric_r, 4),
            friction_drag_pct=round(fric_drag, 2),
        )

        return ComprehensivePerformanceAudit(
            starting_capital_usd=starting_capital,
            ending_equity_usd=round(equity, 4),
            net_profit_usd=round(total_pnl, 4),
            total_return_pct=round(total_ret_pct, 4),
            total_trades=n,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            gross_profit_usd=round(gross_profit, 4),
            gross_loss_usd=round(gross_loss, 4),
            avg_win_usd=round(avg_win, 4),
            avg_loss_usd=round(avg_loss, 4),
            payoff_ratio=round(payoff, 4),
            total_net_r=round(total_net_r, 4),
            expectancy_r=round(exp_r, 4),
            profit_factor_r=round(pf_r, 4),
            std_dev_r=round(std_dev_r, 4),
            drawdown=dd_metrics,
            risk_adjusted=risk_adj,
            tail_risk=tail_metrics,
            friction=fric_metrics,
        )

    @classmethod
    def reconcile_two_sources(
        cls,
        source_a: Dict[str, Any],
        source_b: Dict[str, Any],
        tolerance: float = 1e-3,
    ) -> Tuple[bool, List[str]]:
        """
        Reconciles two independent calculations of performance metrics.
        Returns True if identical within tolerance, or False with detailed discrepancies.
        """
        discrepancies = []
        pf_key = "profit_factor_r" if ("profit_factor_r" in source_a and "profit_factor_r" in source_b) else "profit_factor"
        keys_to_check = [
            ("ending_equity_usd", "Ending Equity"),
            ("total_net_r", "Total Net R"),
            ("total_trades", "Total Trades"),
            ("win_rate", "Win Rate"),
            (pf_key, "Profit Factor"),
        ]

        for key, name in keys_to_check:
            val_a = source_a.get(key)
            val_b = source_b.get(key)
            if val_a is None or val_b is None:
                discrepancies.append(f"Missing key '{key}' in one of the sources (A={val_a}, B={val_b})")
                continue

            diff = abs(float(val_a) - float(val_b))
            if diff > tolerance:
                discrepancies.append(
                    f"{name} mismatch: Source A={val_a} vs Source B={val_b} (diff={diff:.6f} > {tolerance})"
                )

        reconciled = len(discrepancies) == 0
        return reconciled, discrepancies
