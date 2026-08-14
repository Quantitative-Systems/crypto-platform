"""
Product 04 — Research Laboratory: Exit Reason Attribution
Decomposes performance across HTF TP, MTF Structural Trailing, and Initial LTF SL exits.
"""

from typing import List, Dict, Any
from research.simulation.trade_ledger import SimulatedTrade


class ExitAttributionEngine:
    """
    Analyzes and compares performance across different exit types.
    """

    @staticmethod
    def analyze(closed_trades: List[SimulatedTrade]) -> Dict[str, Any]:
        categories = ["HTF_TP", "MTF_STRUCTURAL_TRAIL", "INITIAL_LTF_SL", "OTHER"]
        breakdown: Dict[str, Dict[str, Any]] = {}

        for cat in categories:
            matching = [
                t for t in closed_trades 
                if (t.exit_reason == cat) or (cat == "OTHER" and t.exit_reason not in ["HTF_TP", "MTF_STRUCTURAL_TRAIL", "INITIAL_LTF_SL"])
            ]
            count = len(matching)
            pnls = [t.realized_pnl for t in matching if t.realized_pnl is not None]
            r_multiples = [t.realized_rr for t in matching if t.realized_rr is not None]

            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]

            total_pnl = sum(pnls) if pnls else 0.0
            avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
            win_rate = len(wins) / count if count > 0 else 0.0

            breakdown[cat] = {
                "trade_count": count,
                "percentage_of_total": round(count / len(closed_trades), 4) if closed_trades else 0.0,
                "win_count": len(wins),
                "loss_count": len(losses),
                "win_rate": round(win_rate, 4),
                "total_pnl_usd": round(total_pnl, 2),
                "avg_realized_r": round(avg_r, 4),
                "r_multiples": [round(r, 4) for r in r_multiples]
            }

        return breakdown
