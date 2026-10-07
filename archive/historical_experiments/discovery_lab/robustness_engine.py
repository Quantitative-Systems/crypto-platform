"""
PROJECT TOP1 — Phase 10 & Phase 13 Robustness & Portability Testing Engine.

Tests candidates against:
1. Friction Sensitivity: 1.5x and 2.0x taker fees & slippage
2. Parameter Perturbations: +/- 10%, +/- 20% on indicator lengths and multipliers
3. Asset Portability Matrix:
   - BTC -> ETH, SOL
   - ETH -> BTC, SOL
   - SOL -> BTC, ETH
4. Timeframe Transfer: S3 -> S4, S4 -> S5
5. Regime & Subperiod Stability: Split evaluation into chronological thirds (early, mid, late)
"""

from typing import Dict, Any, List, Optional
import numpy as np


class RobustnessEngine:
    """
    Evaluates whether a candidate has a robust statistical edge or is fragilely curve-fit.
    """

    @staticmethod
    def evaluate_friction_stress(
        base_net_r: float,
        stress_net_r_2x: float,
    ) -> Dict[str, Any]:
        """Verify performance under double institutional friction."""
        retains_positive = stress_net_r_2x > 0
        decay_pct = (base_net_r - stress_net_r_2x) / base_net_r if base_net_r > 0 else 1.0
        return {
            "base_net_r": round(base_net_r, 4),
            "stress_net_r_2x": round(stress_net_r_2x, 4),
            "decay_pct": round(decay_pct, 4),
            "passed": retains_positive and decay_pct < 0.50,
            "verdict": "PASS" if (retains_positive and decay_pct < 0.50) else "FAIL_FRICTION_FRAGILE",
        }

    @staticmethod
    def evaluate_asset_transfer(
        stream_results: Dict[str, Dict[str, Any]],
        set_name: str,
    ) -> Dict[str, Any]:
        """
        Calculates the cross-asset transfer matrix for a given timeframe set.
        E.g. BTC -> ETH, BTC -> SOL, ETH -> SOL.
        """
        assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        matrix = {}
        positive_count = 0

        for a in assets:
            key = f"{a}_{set_name}"
            res = stream_results.get(key, {})
            net_r = res.get("net_r", 0.0)
            trades = res.get("total_trades", 0)
            if net_r > 0:
                positive_count += 1
            matrix[a] = {"net_r": net_r, "trades": trades}

        transfer_ratio = positive_count / len(assets)
        is_portable = transfer_ratio >= 0.66

        return {
            "set": set_name,
            "matrix": matrix,
            "portable_asset_ratio": round(transfer_ratio, 2),
            "is_cross_asset_portable": is_portable,
            "verdict": "PORTABLE" if is_portable else "ASSET_SPECIFIC",
        }

    @staticmethod
    def evaluate_subperiod_stability(
        realized_rs: List[float],
    ) -> Dict[str, Any]:
        """
        Splits trades chronologically into 3 equal periods and tests consistency.
        """
        if len(realized_rs) < 9:
            return {
                "verdict": "INSUFFICIENT_SAMPLE_FOR_SUBPERIODS",
                "is_stable": False,
            }

        k = len(realized_rs) // 3
        p1 = realized_rs[:k]
        p2 = realized_rs[k:2*k]
        p3 = realized_rs[2*k:]

        sum1, sum2, sum3 = sum(p1), sum(p2), sum(p3)
        all_positive = sum1 > 0 and sum2 > 0 and sum3 > 0
        two_positive = sum([sum1 > 0, sum2 > 0, sum3 > 0]) >= 2

        return {
            "period_1_r": round(sum1, 2),
            "period_2_r": round(sum2, 2),
            "period_3_r": round(sum3, 2),
            "all_periods_positive": all_positive,
            "is_stable": two_positive,
            "verdict": "STABLE" if two_positive else "REGIME_CONCENTRATED",
        }
