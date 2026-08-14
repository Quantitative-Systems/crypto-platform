"""
Product 04 — Research Laboratory: Metrics Engine
Computes mathematically rigorous performance metrics, R-multiple distributions, 
and handles zero-division edge cases with semantic values (NOT_AVAILABLE, INFINITE, UNDEFINED).
"""

from typing import List, Dict, Any, Union
import math
from research.simulation.trade_ledger import SimulatedTrade, TradeLedger


class MetricsEngine:
    """
    Computes exact statistical metrics from closed trades and equity curves.
    """

    @staticmethod
    def calculate_metrics(
        closed_trades: List[SimulatedTrade],
        ledger: TradeLedger,
        risk_free_rate: float = 0.0
    ) -> Dict[str, Any]:
        total_trades = len(closed_trades)

        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "gross_profit_usd": 0.0,
                "gross_loss_usd": 0.0,
                "net_profit_usd": 0.0,
                "total_friction_usd": 0.0,
                "avg_win_usd": 0.0,
                "avg_loss_usd": 0.0,
                "profit_factor": "NOT_AVAILABLE",
                "expectancy_usd": "NOT_AVAILABLE",
                "expectancy_r": "NOT_AVAILABLE",
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": "NOT_AVAILABLE",
                "sortino_ratio": "NOT_AVAILABLE",
                "average_r": "NOT_AVAILABLE",
                "median_r": "NOT_AVAILABLE",
                "r_multiples": []
            }

        pnls = [t.realized_pnl for t in closed_trades if t.realized_pnl is not None]
        r_multiples = [t.realized_rr for t in closed_trades if t.realized_rr is not None]

        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        breakeven_trades = [p for p in pnls if p == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        breakeven_count = len(breakeven_trades)

        win_rate = win_count / total_trades
        loss_rate = loss_count / total_trades

        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        net_profit = gross_profit - gross_loss
        total_friction = sum(t.total_friction_usd for t in closed_trades)

        avg_win = gross_profit / win_count if win_count > 0 else 0.0
        avg_loss = gross_loss / loss_count if loss_count > 0 else 0.0

        # Profit Factor handling
        if gross_loss == 0.0:
            profit_factor: Union[float, str] = "INFINITE" if gross_profit > 0 else 0.0
        else:
            profit_factor = gross_profit / gross_loss

        # Expectancy in USD
        expectancy_usd = (win_rate * avg_win) - (loss_rate * avg_loss)

        # R-multiples calculation
        winning_r = [r for r in r_multiples if r > 0]
        losing_r = [abs(r) for r in r_multiples if r < 0]
        avg_win_r = sum(winning_r) / len(winning_r) if winning_r else 0.0
        avg_loss_r = sum(losing_r) / len(losing_r) if losing_r else 0.0
        expectancy_r = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

        sorted_r = sorted(r_multiples)
        median_r = sorted_r[len(sorted_r) // 2] if sorted_r else 0.0
        avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

        # Max Drawdown from ledger
        max_drawdown = ledger.max_drawdown_pct

        # Sharpe & Sortino Ratios (per trade return distribution)
        mean_pnl = net_profit / total_trades
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / total_trades if total_trades > 1 else 0.0
        std_dev = math.sqrt(variance)

        downside_variance = sum((p - mean_pnl) ** 2 for p in losing_trades) / total_trades if losing_trades else 0.0
        downside_std_dev = math.sqrt(downside_variance)

        if std_dev == 0.0:
            sharpe_ratio: Union[float, str] = "INFINITE" if (mean_pnl - risk_free_rate) > 0 else "UNDEFINED"
        else:
            sharpe_ratio = (mean_pnl - risk_free_rate) / std_dev

        if downside_std_dev == 0.0:
            sortino_ratio: Union[float, str] = "INFINITE" if (mean_pnl - risk_free_rate) > 0 else "UNDEFINED"
        else:
            sortino_ratio = (mean_pnl - risk_free_rate) / downside_std_dev

        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "breakeven_count": breakeven_count,
            "win_rate": round(win_rate, 4),
            "loss_rate": round(loss_rate, 4),
            "gross_profit_usd": round(gross_profit, 2),
            "gross_loss_usd": round(gross_loss, 2),
            "net_profit_usd": round(net_profit, 2),
            "total_friction_usd": round(total_friction, 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "profit_factor": profit_factor if isinstance(profit_factor, str) else round(profit_factor, 4),
            "expectancy_usd": round(expectancy_usd, 2),
            "expectancy_r": round(expectancy_r, 4),
            "max_drawdown_pct": round(max_drawdown, 4),
            "sharpe_ratio": sharpe_ratio if isinstance(sharpe_ratio, str) else round(sharpe_ratio, 4),
            "sortino_ratio": sortino_ratio if isinstance(sortino_ratio, str) else round(sortino_ratio, 4),
            "average_r": round(avg_r, 4),
            "median_r": round(median_r, 4),
            "r_multiples": [round(r, 4) for r in r_multiples]
        }
