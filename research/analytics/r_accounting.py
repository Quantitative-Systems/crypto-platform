"""
PROJECT TOP1 — Institutional Standardized R-Multiple Accounting Engine.

Implements mathematically rigorous R-based metrics for all trades:
- Planned R: |TP3 - Entry| / |Entry - Initial Stop|
- Realized R: Net PnL / (Entry Equity * 1%)
- Net R: Sum of all realized R
- Expectancy in R: Net R / Total Trades
- Profit Factor in R: Sum(Win R) / |Sum(Loss R)|
- Max Drawdown in R: Peak-to-trough decline of cumulative Realized R
- Average R & Median R
- Win Rate & Loss Rate
- MAE (Maximum Adverse Excursion in R)
- MFE (Maximum Favorable Excursion in R)
"""

from typing import List, Dict, Any, Union, Optional, Tuple
import math
import numpy as np


class RAccountingEngine:
    """
    Standardized R-Multiple Accounting & Metrics Engine for Project TOP1.
    All strategy evaluations must be reported primarily in R.
    """

    @staticmethod
    def calculate_trade_r(
        net_pnl: float,
        entry_equity: float,
        risk_pct: float = 0.01,
    ) -> float:
        """Calculate Realized R for a single closed trade."""
        initial_risk_dollars = entry_equity * risk_pct
        if initial_risk_dollars <= 0:
            return 0.0
        return net_pnl / initial_risk_dollars

    @staticmethod
    def calculate_excursions(
        direction: int,
        entry_price: float,
        initial_sl: float,
        mfe_price: float,
        mae_price: float,
    ) -> Tuple[float, float]:
        """
        Calculate MFE and MAE in R-multiples.
        Both values are non-negative measuring excursion relative to initial stop distance.
        """
        risk_dist = abs(entry_price - initial_sl)
        if risk_dist <= 0:
            return 0.0, 0.0

        if direction == 1:  # LONG
            mfe_r = max(0.0, (mfe_price - entry_price) / risk_dist)
            mae_r = max(0.0, (entry_price - mae_price) / risk_dist)
        else:  # SHORT
            mfe_r = max(0.0, (entry_price - mfe_price) / risk_dist)
            mae_r = max(0.0, (mae_price - entry_price) / risk_dist)

        return round(mfe_r, 4), round(mae_r, 4)

    @staticmethod
    def compute_stream_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute full standardized R-multiple metrics from a list of trade records.
        """
        total_trades = len(trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "net_r": 0.0,
                "expectancy_r": 0.0,
                "profit_factor_r": "NOT_AVAILABLE",
                "max_drawdown_r": 0.0,
                "average_r": 0.0,
                "median_r": 0.0,
                "avg_win_r": 0.0,
                "avg_loss_r": 0.0,
                "avg_mae_r": 0.0,
                "avg_mfe_r": 0.0,
                "max_mae_r": 0.0,
                "max_mfe_r": 0.0,
                "net_pnl_usd": 0.0,
                "total_fees_usd": 0.0,
                "sample_confidence": "INSUFFICIENT_DATA",
            }

        realized_rs = [float(t["realized_r"]) for t in trades]
        wins = [r for r in realized_rs if r > 0.0]
        losses = [r for r in realized_rs if r < 0.0]
        breakevens = [r for r in realized_rs if r == 0.0]

        win_count = len(wins)
        loss_count = len(losses)
        breakeven_count = len(breakevens)

        win_rate = win_count / total_trades
        loss_rate = loss_count / total_trades

        net_r = sum(realized_rs)
        average_r = net_r / total_trades
        median_r = float(np.median(realized_rs))

        sum_win_r = sum(wins)
        sum_loss_r = abs(sum(losses))

        avg_win_r = sum_win_r / win_count if win_count > 0 else 0.0
        avg_loss_r = sum_loss_r / loss_count if loss_count > 0 else 0.0

        if sum_loss_r == 0.0:
            profit_factor_r: Union[float, str] = "INFINITE" if sum_win_r > 0 else 0.0
        else:
            profit_factor_r = round(sum_win_r / sum_loss_r, 4)

        expectancy_r = (win_rate * avg_win_r) - (loss_rate * avg_loss_r)

        # Drawdown calculation in R
        cum_r = np.cumsum(realized_rs)
        running_max = np.maximum.accumulate(cum_r)
        drawdown_series = running_max - cum_r
        max_drawdown_r = float(np.max(drawdown_series)) if len(drawdown_series) > 0 else 0.0

        # MAE and MFE statistics
        mae_list = [float(t.get("mae_r", 0.0)) for t in trades]
        mfe_list = [float(t.get("mfe_r", 0.0)) for t in trades]

        avg_mae_r = float(np.mean(mae_list)) if mae_list else 0.0
        avg_mfe_r = float(np.mean(mfe_list)) if mfe_list else 0.0
        max_mae_r = float(np.max(mae_list)) if mae_list else 0.0
        max_mfe_r = float(np.max(mfe_list)) if mfe_list else 0.0

        net_pnl_usd = sum(float(t.get("net_pnl", 0.0)) for t in trades)
        total_fees_usd = sum(float(t.get("entry_fee", 0.0)) + float(t.get("exit_fee", 0.0)) for t in trades)

        # Statistical sample confidence
        if total_trades >= 30:
            sample_confidence = "STATISTICALLY_EVALUABLE"
        elif total_trades >= 10:
            sample_confidence = "PRELIMINARY_SAMPLE"
        else:
            sample_confidence = "SAMPLE_TOO_SMALL"

        return {
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "breakeven_count": breakeven_count,
            "win_rate": round(win_rate, 4),
            "loss_rate": round(loss_rate, 4),
            "net_r": round(net_r, 4),
            "expectancy_r": round(expectancy_r, 4),
            "profit_factor_r": profit_factor_r,
            "max_drawdown_r": round(max_drawdown_r, 4),
            "average_r": round(average_r, 4),
            "median_r": round(median_r, 4),
            "avg_win_r": round(avg_win_r, 4),
            "avg_loss_r": round(avg_loss_r, 4),
            "avg_mae_r": round(avg_mae_r, 4),
            "avg_mfe_r": round(avg_mfe_r, 4),
            "max_mae_r": round(max_mae_r, 4),
            "max_mfe_r": round(max_mfe_r, 4),
            "net_pnl_usd": round(net_pnl_usd, 2),
            "total_fees_usd": round(total_fees_usd, 2),
            "sample_confidence": sample_confidence,
        }
