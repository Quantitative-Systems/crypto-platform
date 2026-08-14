"""
Product 04 — Research Laboratory: Failure Analysis & Market Regime Classifier
Identifies failure modes for losing trades and evaluates performance across market regimes.
"""

from typing import List, Dict, Any
from research.simulation.trade_ledger import SimulatedTrade


class FailureAnalyzer:
    """
    Categorizes the structural failure modes of losing trades.
    """

    @staticmethod
    def classify_failure_modes(closed_trades: List[SimulatedTrade]) -> Dict[str, Any]:
        losing_trades = [t for t in closed_trades if t.realized_pnl is not None and t.realized_pnl < 0]
        
        failure_counts: Dict[str, int] = {
            "INITIAL_STRUCTURAL_INVALIDATION": 0,
            "MTF_TRAIL_REVERSAL": 0,
            "TARGET_UNREACHED_REVERSAL": 0,
            "OTHER": 0
        }

        for trade in losing_trades:
            if trade.exit_reason == "INITIAL_LTF_SL":
                failure_counts["INITIAL_STRUCTURAL_INVALIDATION"] += 1
            elif trade.exit_reason == "MTF_STRUCTURAL_TRAIL":
                failure_counts["MTF_TRAIL_REVERSAL"] += 1
            elif trade.exit_reason == "HTF_TP":
                failure_counts["TARGET_UNREACHED_REVERSAL"] += 1
            else:
                failure_counts["OTHER"] += 1

        total_losses = len(losing_trades)
        breakdown: Dict[str, Any] = {}
        for reason, count in failure_counts.items():
            breakdown[reason] = {
                "count": count,
                "percentage_of_losses": round(count / total_losses, 4) if total_losses > 0 else 0.0
            }

        return {
            "total_losing_trades": total_losses,
            "failure_mode_breakdown": breakdown
        }
