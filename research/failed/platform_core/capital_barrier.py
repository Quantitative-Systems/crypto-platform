"""
Platform Core: Institutional 5-Tier Graduated Capital Barrier & Risk Governance Engine
Enforces the inviolable principle: 'The system must be allowed to tell us NO.'
Replaces binary gating with a 5-tier authorization hierarchy:
1. REJECTED_RESEARCH_ONLY (Failed one or more mandatory dimensions)
2. RESEARCH_VALIDATED (Cleared Data Validity & In-Sample Positive Expectancy)
3. PAPER_ELIGIBLE (Cleared Statistical Significance, OOS Profitability & Cost Shock Robustness)
4. MICRO_LIVE_ELIGIBLE (Cleared Walk-Forward Generalization, Parameter Stability & Risk Limits)
5. PRODUCTION_ELIGIBLE (Cleared Live Execution Realism, Broker Reconciliation & Scale Audits)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional


class CapitalBarrierTier(str, Enum):
    REJECTED_RESEARCH_ONLY = "REJECTED_RESEARCH_ONLY"
    RESEARCH_VALIDATED = "RESEARCH_VALIDATED"
    PAPER_ELIGIBLE = "PAPER_ELIGIBLE"
    MICRO_LIVE_ELIGIBLE = "MICRO_LIVE_ELIGIBLE"
    PRODUCTION_ELIGIBLE = "PRODUCTION_ELIGIBLE"


# For backward compatibility with existing tests referencing CapitalBarrierDecision
CapitalBarrierDecision = CapitalBarrierTier


class CapitalBarrierBreachError(Exception):
    """Raised when an unauthorized strategy attempts to access live production execution."""
    pass


@dataclass
class CapitalBarrierEvaluation:
    hypothesis_id: str
    decision: CapitalBarrierTier
    passed_all_gates: bool
    rejection_reasons: List[str]
    dimension_reports: Dict[str, Any]
    provenance: Dict[str, str] = field(default_factory=lambda: {
        "hierarchy": "Wealth Multiplier Systems -> Quantitative Systems Platform -> Product 01: Crypto Platform",
        "standard": "v2.0-UNIFIED-CANONICAL-LOCKED"
    })


class CapitalBarrier:
    """
    Evaluates quantitative strategy hypotheses through the 10-Dimension Risk Governance Engine
    and assigns a 5-Tier Authorization Level.
    """

    MIN_SAMPLE_SIZE = 30
    MIN_EXPECTANCY_R = 0.0
    MIN_BOOTSTRAP_LOWER_R = 0.0
    MIN_WALK_FORWARD_RATIO = 0.70
    MAX_ALLOWED_DRAWDOWN_PCT = 20.0
    MAX_PARAMETER_SENSITIVITY_PCT = 30.0

    @staticmethod
    def evaluate_deployment_eligibility(
        hypothesis_id: str,
        total_trades: int,
        net_expectancy_r: float,
        bootstrap_lower_ci_r: float,
        walk_forward_ratio: Optional[float],
        max_drawdown_pct: float,
        cost_shock_expectancy_r: float,
        data_certified: bool = True,
        mht_survived: bool = True,
        parameter_sensitivity_pct: float = 15.0,
        oos_expectancy_r: Optional[float] = None,
        regime_stable: bool = True,
        execution_validated: bool = True
    ) -> CapitalBarrierEvaluation:
        """
        Runs candidate strategy through all 10 Capital Barrier institutional dimensions
        and assigns a 5-Tier Authorization Level.
        """
        rejection_reasons: List[str] = []
        dimensions: Dict[str, str] = {}

        # 1. Data Validity
        if not data_certified:
            rejection_reasons.append("DIM_1_DATA_VALIDITY: Dataset not certified or manifest missing")
            dimensions["dim_1_data_validity"] = "FAILED"
        else:
            dimensions["dim_1_data_validity"] = "PASSED"

        # 2. Alpha Expectancy
        if net_expectancy_r <= CapitalBarrier.MIN_EXPECTANCY_R:
            rejection_reasons.append(
                f"DIM_2_ALPHA_EXPECTANCY: Negative post-friction expectancy ({net_expectancy_r:.4f}R <= 0.0R)"
            )
            dimensions["dim_2_alpha_expectancy"] = "FAILED"
        else:
            dimensions["dim_2_alpha_expectancy"] = "PASSED"

        # 3. Statistical Significance
        if total_trades < CapitalBarrier.MIN_SAMPLE_SIZE:
            rejection_reasons.append(
                f"DIM_3_STATISTICAL_SAMPLE: Insufficient sample size (N={total_trades} < {CapitalBarrier.MIN_SAMPLE_SIZE})"
            )
            dimensions["dim_3_statistical_significance"] = "FAILED"
        elif bootstrap_lower_ci_r <= CapitalBarrier.MIN_BOOTSTRAP_LOWER_R:
            rejection_reasons.append(
                f"DIM_3_STATISTICAL_CI: Bootstrap 95% lower bound ({bootstrap_lower_ci_r:.4f}R <= 0.0R)"
            )
            dimensions["dim_3_statistical_significance"] = "FAILED"
        elif not mht_survived:
            rejection_reasons.append("DIM_3_MHT_PENALTY: Fails Bonferroni/Holm trial count penalty")
            dimensions["dim_3_statistical_significance"] = "FAILED"
        else:
            dimensions["dim_3_statistical_significance"] = "PASSED"

        # 4. Out-of-Sample Profitability
        if oos_expectancy_r is not None and oos_expectancy_r <= 0.0:
            rejection_reasons.append(
                f"DIM_4_OOS_PROFITABILITY: Non-positive OOS expectancy ({oos_expectancy_r:.4f}R <= 0.0R)"
            )
            dimensions["dim_4_oos_profitability"] = "FAILED"
        else:
            dimensions["dim_4_oos_profitability"] = "PASSED"

        # 5. Walk-Forward Robustness
        if walk_forward_ratio is None or walk_forward_ratio < CapitalBarrier.MIN_WALK_FORWARD_RATIO:
            wfr_str = f"{walk_forward_ratio:.2f}" if walk_forward_ratio is not None else "None"
            rejection_reasons.append(
                f"DIM_5_WALK_FORWARD: Generalization ratio {wfr_str} < {CapitalBarrier.MIN_WALK_FORWARD_RATIO:.2f}"
            )
            dimensions["dim_5_walk_forward"] = "FAILED"
        else:
            dimensions["dim_5_walk_forward"] = "PASSED"

        # 6. Parameter Cliff Stability
        if parameter_sensitivity_pct > CapitalBarrier.MAX_PARAMETER_SENSITIVITY_PCT:
            rejection_reasons.append(
                f"DIM_6_PARAMETER_CLIFF: Sensitivity variance {parameter_sensitivity_pct:.1f}% > {CapitalBarrier.MAX_PARAMETER_SENSITIVITY_PCT:.1f}%"
            )
            dimensions["dim_6_parameter_cliff"] = "FAILED"
        else:
            dimensions["dim_6_parameter_cliff"] = "PASSED"

        # 7. Cost & Slippage Robustness
        if cost_shock_expectancy_r <= 0.0:
            rejection_reasons.append(
                f"DIM_7_COST_SHOCK: Edge destroyed under transaction cost shock ({cost_shock_expectancy_r:.4f}R <= 0.0R)"
            )
            dimensions["dim_7_cost_robustness"] = "FAILED"
        else:
            dimensions["dim_7_cost_robustness"] = "PASSED"

        # 8. Drawdown & Risk Limits
        if max_drawdown_pct > CapitalBarrier.MAX_ALLOWED_DRAWDOWN_PCT:
            rejection_reasons.append(
                f"DIM_8_RISK_LIMITS: Max Drawdown {max_drawdown_pct:.1f}% > {CapitalBarrier.MAX_ALLOWED_DRAWDOWN_PCT:.1f}%"
            )
            dimensions["dim_8_risk_limits"] = "FAILED"
        else:
            dimensions["dim_8_risk_limits"] = "PASSED"

        # 9. Regime Stability
        if not regime_stable:
            rejection_reasons.append("DIM_9_REGIME_STABILITY: Strategy exhibits catastrophic losses in range chop regimes")
            dimensions["dim_9_regime_stability"] = "FAILED"
        else:
            dimensions["dim_9_regime_stability"] = "PASSED"

        # 10. Execution Realism
        if not execution_validated:
            rejection_reasons.append("DIM_10_EXECUTION_REALISM: Strategy has not completed Paper/Shadow validation")
            dimensions["dim_10_execution_realism"] = "FAILED"
        else:
            dimensions["dim_10_execution_realism"] = "PASSED"

        # Graduated Authorization Hierarchy
        if not data_certified or net_expectancy_r <= 0.0:
            decision = CapitalBarrierTier.REJECTED_RESEARCH_ONLY
        elif total_trades < CapitalBarrier.MIN_SAMPLE_SIZE or bootstrap_lower_ci_r <= 0.0:
            decision = CapitalBarrierTier.RESEARCH_VALIDATED
        elif walk_forward_ratio is None or walk_forward_ratio < CapitalBarrier.MIN_WALK_FORWARD_RATIO or cost_shock_expectancy_r <= 0.0:
            decision = CapitalBarrierTier.PAPER_ELIGIBLE
        elif not execution_validated:
            decision = CapitalBarrierTier.MICRO_LIVE_ELIGIBLE
        else:
            decision = CapitalBarrierTier.PRODUCTION_ELIGIBLE

        passed = len(rejection_reasons) == 0
        if not passed:
            decision = CapitalBarrierTier.REJECTED_RESEARCH_ONLY

        return CapitalBarrierEvaluation(
            hypothesis_id=hypothesis_id,
            decision=decision,
            passed_all_gates=passed,
            rejection_reasons=rejection_reasons,
            dimension_reports=dimensions
        )

    @staticmethod
    def enforce_barrier(evaluation: CapitalBarrierEvaluation, allow_research_sandbox: bool = False):
        if not evaluation.passed_all_gates and not allow_research_sandbox:
            reasons_str = "; ".join(evaluation.rejection_reasons)
            raise CapitalBarrierBreachError(
                f"CAPITAL BARRIER BREACH: Hypothesis '{evaluation.hypothesis_id}' rejected for live capital (Tier: {evaluation.decision.value}). Reasons: {reasons_str}"
            )
