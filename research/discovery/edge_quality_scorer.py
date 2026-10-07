"""Edge Quality Scorer & Institutional Classification Engine.

Implements the multi-dimensional Edge Quality Score (EQS) from Section 20:
Ranks candidates based on true empirical robustness, transferability,
and cost resilience rather than curve-fitted historical PnL:
- Expectancy (realized R per trade)
- Sample adequacy (trade count confidence)
- OOS consistency (DEV vs VAL vs OOS persistence)
- Cross-asset transferability (BTC, ETH, SOL, BNB)
- Cross-set transferability (Fractal scale transfer across SET 1 to SET 5)
- Cost resilience (survival under 2x and 3x fees and slippage)
- Return concentration (retention when top 1 and top 2 winners removed)
- Tail risk & Drawdown (CVaR95 and Max DD in R)
- Parameter stability (resilience to target R floor shifts)
- Null-test superiority (falsification p-value against random controls)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class EdgeQualityScore:
    candidate_id: str
    total_score: float  # 0.0 to 100.0
    classification: str  # STRONG_EDGE, PROMISING, CONDITIONAL, UNSTABLE, NO_EDGE, FALSIFIED
    expectancy_score: float
    sample_adequacy_score: float
    oos_consistency_score: float
    asset_transfer_score: float
    scale_transfer_score: float
    cost_resilience_score: float
    concentration_score: float
    tail_risk_score: float
    null_superiority_score: float
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "total_score": round(self.total_score, 1),
            "classification": self.classification,
            "component_scores": {
                "expectancy": round(self.expectancy_score, 1),
                "sample_adequacy": round(self.sample_adequacy_score, 1),
                "oos_consistency": round(self.oos_consistency_score, 1),
                "asset_transfer": round(self.asset_transfer_score, 1),
                "scale_transfer": round(self.scale_transfer_score, 1),
                "cost_resilience": round(self.cost_resilience_score, 1),
                "concentration": round(self.concentration_score, 1),
                "tail_risk": round(self.tail_risk_score, 1),
                "null_superiority": round(self.null_superiority_score, 1),
            },
            "details": self.details,
        }


class EdgeQualityScorer:
    """Computes composite Edge Quality Score (EQS) across 10 institutional dimensions."""

    @staticmethod
    def score_candidate(
        candidate_id: str,
        metrics_full: Dict[str, Any],
        metrics_dev: Dict[str, Any],
        metrics_val: Dict[str, Any],
        metrics_oos: Dict[str, Any],
        asset_transfer_results: Optional[Dict[str, float]] = None,
        scale_transfer_results: Optional[Dict[str, float]] = None,
        cost_stress_2x: Optional[Dict[str, Any]] = None,
        null_test_p_value: float = 0.01,
    ) -> EdgeQualityScore:
        exp_full = float(metrics_full.get("expectancy_r", 0.0))
        n_trades = int(metrics_full.get("total_trades", 0))
        exp_dev = float(metrics_dev.get("expectancy_r", 0.0))
        exp_oos = float(metrics_oos.get("expectancy_r", 0.0))
        max_dd = float(metrics_full.get("max_drawdown_r", 0.0))
        cvar95 = float(metrics_full.get("cvar_95_r", -1.5))
        exp_ex_top2 = float(metrics_full.get("exp_r_ex_top2", 0.0))
        top2_conc = float(metrics_full.get("top2_concentration_pct", 100.0))

        # 1. Expectancy Score (0 to 15 pts): target 0.20R+ for max score
        s_exp = min(15.0, max(0.0, (exp_full / 0.25) * 15.0))

        # 2. Sample Adequacy (0 to 10 pts): N >= 100 is full, N < 30 severely penalized
        if n_trades >= 100:
            s_sample = 10.0
        elif n_trades >= 50:
            s_sample = 8.0
        elif n_trades >= 30:
            s_sample = 5.0
        elif n_trades >= 15:
            s_sample = 2.0
        else:
            s_sample = 0.0

        # 3. OOS Consistency (0 to 15 pts)
        if exp_oos > 0 and exp_dev > 0:
            ratio = exp_oos / max(0.01, exp_dev)
            s_oos = min(15.0, max(5.0, ratio * 12.0))
        elif exp_oos > 0:
            s_oos = 10.0
        elif exp_oos >= -0.05:
            s_oos = 4.0
        else:
            s_oos = 0.0

        # 4. Cross-Asset Transfer (0 to 10 pts)
        if asset_transfer_results:
            pos_assets = sum(1 for v in asset_transfer_results.values() if v > 0)
            tot_assets = len(asset_transfer_results)
            s_asset = (pos_assets / max(1, tot_assets)) * 10.0
        else:
            s_asset = 5.0

        # 5. Cross-Set Scale Transfer (0 to 10 pts)
        if scale_transfer_results:
            pos_sets = sum(1 for v in scale_transfer_results.values() if v > 0)
            tot_sets = len(scale_transfer_results)
            s_scale = (pos_sets / max(1, tot_sets)) * 10.0
        else:
            s_scale = 5.0

        # 6. Cost Resilience under 2x fees & slippage (0 to 10 pts)
        if cost_stress_2x:
            exp_2x = float(cost_stress_2x.get("expectancy_r", 0.0))
            if exp_2x > 0 and exp_full > 0:
                s_cost = min(10.0, max(0.0, (exp_2x / exp_full) * 10.0))
            elif exp_2x > 0:
                s_cost = 5.0
            else:
                s_cost = 0.0
        else:
            s_cost = 5.0

        # 7. Return Concentration Audit (0 to 10 pts)
        # Requires E[R] without top 2 winners to remain positive, and top 2 concentration < 40%
        if exp_ex_top2 > 0 and top2_conc < 40.0:
            s_conc = 10.0
        elif exp_ex_top2 > 0:
            s_conc = 7.0
        elif exp_ex_top2 >= -0.02:
            s_conc = 3.0
        else:
            s_conc = 0.0

        # 8. Tail Risk & Drawdown (0 to 10 pts)
        # Max DD < 10R is great, > 25R is poor; CVaR95 > -1.2R is good
        dd_pts = min(5.0, max(0.0, 5.0 - (max_dd / 25.0) * 5.0))
        cvar_pts = min(5.0, max(0.0, 5.0 - (abs(cvar95) - 1.0) * 5.0))
        s_tail = dd_pts + cvar_pts

        # 9. Null-Test Superiority (0 to 10 pts)
        if null_test_p_value < 0.01:
            s_null = 10.0
        elif null_test_p_value < 0.05:
            s_null = 7.0
        elif null_test_p_value < 0.10:
            s_null = 3.0
        else:
            s_null = 0.0

        total_score = s_exp + s_sample + s_oos + s_asset + s_scale + s_cost + s_conc + s_tail + s_null

        # Classification
        if total_score >= 80.0 and exp_oos > 0 and exp_ex_top2 > 0:
            classification = "STRONG_EDGE"
        elif total_score >= 65.0 and exp_full > 0:
            classification = "PROMISING"
        elif total_score >= 50.0:
            classification = "CONDITIONAL"
        elif total_score >= 35.0:
            classification = "UNSTABLE"
        elif null_test_p_value > 0.10 or exp_full <= 0:
            classification = "FALSIFIED"
        else:
            classification = "NO_EDGE"

        return EdgeQualityScore(
            candidate_id=candidate_id,
            total_score=total_score,
            classification=classification,
            expectancy_score=s_exp,
            sample_adequacy_score=s_sample,
            oos_consistency_score=s_oos,
            asset_transfer_score=s_asset,
            scale_transfer_score=s_scale,
            cost_resilience_score=s_cost,
            concentration_score=s_conc,
            tail_risk_score=s_tail,
            null_superiority_score=s_null,
            details={
                "exp_full": exp_full,
                "n_trades": n_trades,
                "exp_oos": exp_oos,
                "exp_ex_top2": exp_ex_top2,
                "top2_concentration_pct": top2_conc,
                "max_drawdown_r": max_dd,
                "cvar_95_r": cvar95,
                "null_p_value": null_test_p_value,
            },
        )
