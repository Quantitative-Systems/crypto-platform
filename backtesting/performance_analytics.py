"""
Product 01: Crypto Platform - Institutional Performance Analytics Engine
Calculates 18-point performance statistics including Profit Factor, Sharpe Ratio, Calmar, Streaks & Splits.
"""

from typing import List, Dict, Any
import math


class PerformanceAnalytics:

    @staticmethod
    def compute_deep_metrics(trade_history: List[Dict[str, Any]], starting_balance: float = 1000.0) -> Dict[str, Any]:
        """Calculates 18-point institutional performance report from trade execution history."""
        total_trades = len(trade_history)
        if total_trades == 0:
            return {"total_trades": 0, "status": "NO_TRADES_EXECUTED"}

        wins = [t for t in trade_history if t.get("pnl_usd", 0) > 0]
        losses = [t for t in trade_history if t.get("pnl_usd", 0) < 0]

        gross_profit = sum(t.get("pnl_usd", 0) for t in wins)
        gross_loss = abs(sum(t.get("pnl_usd", 0) for t in losses))
        net_pnl = gross_profit - gross_loss

        # Profit Factor
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else gross_profit

        # Win Rate & Streaks
        win_rate_pct = (len(wins) / total_trades) * 100.0
        max_win_streak = 0
        max_loss_streak = 0
        curr_win = 0
        curr_loss = 0

        for t in trade_history:
            if t.get("pnl_usd", 0) > 0:
                curr_win += 1
                curr_loss = 0
                max_win_streak = max(max_win_streak, curr_win)
            elif t.get("pnl_usd", 0) < 0:
                curr_loss += 1
                curr_win = 0
                max_loss_streak = max(max_loss_streak, curr_loss)

        # Long vs Short Split
        longs = [t for t in trade_history if t.get("action") == "BUY"]
        shorts = [t for t in trade_history if t.get("action") == "SELL"]

        long_wins = [t for t in longs if t.get("pnl_usd", 0) > 0]
        short_wins = [t for t in shorts if t.get("pnl_usd", 0) > 0]

        long_win_rate = (len(long_wins) / len(longs) * 100.0) if longs else 0.0
        short_win_rate = (len(short_wins) / len(shorts) * 100.0) if shorts else 0.0

        # Equity Curve & Drawdown Tracking
        equity_curve = [starting_balance]
        peak = starting_balance
        max_drawdown_pct = 0.0

        for t in trade_history:
            current_bal = equity_curve[-1] + t.get("pnl_usd", 0)
            equity_curve.append(current_bal)
            if current_bal > peak:
                peak = current_bal
            dd = (peak - current_bal) / peak * 100.0 if peak > 0 else 0.0
            max_drawdown_pct = max(max_drawdown_pct, dd)

        final_balance = equity_curve[-1]
        net_return_pct = ((final_balance - starting_balance) / starting_balance) * 100.0

        # Return Ratios (Sharpe & Calmar)
        returns_pct = [(equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1] for i in range(1, len(equity_curve))]
        avg_ret = sum(returns_pct) / len(returns_pct) if returns_pct else 0.0
        std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns_pct) / len(returns_pct)) if len(returns_pct) > 1 else 0.01

        sharpe_ratio = (avg_ret / std_ret) * math.sqrt(252) if std_ret > 0 else 0.0
        calmar_ratio = (net_return_pct / max_drawdown_pct) if max_drawdown_pct > 0 else net_return_pct

        return {
            "total_trades": total_trades,
            "wins_count": len(wins),
            "losses_count": len(losses),
            "win_rate_pct": win_rate_pct,
            "starting_balance": starting_balance,
            "final_balance": final_balance,
            "net_pnl_usd": net_pnl,
            "net_return_pct": net_return_pct,
            "gross_profit_usd": gross_profit,
            "gross_loss_usd": gross_loss,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "calmar_ratio": calmar_ratio,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "long_trades": len(longs),
            "long_win_rate": long_win_rate,
            "short_trades": len(shorts),
            "short_win_rate": short_win_rate,
            "avg_win_usd": (gross_profit / len(wins)) if wins else 0.0,
            "avg_loss_usd": (gross_loss / len(losses)) if losses else 0.0
        }