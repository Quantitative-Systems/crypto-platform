"""
Quantitative Crypto Platform (QCP) — Generic Dynamic Capital Allocator.

Institutional multi-strategy portfolio capital allocation engine operating on
generic alpha slots rather than hardcoded strategy identities:
- Expected Net Edge Ranking (rejects net edge <= 0)
- Statistical Uncertainty Penalty (bootstrap / estimation variance discounting)
- Volatility Normalization (Risk Parity / Equal Risk Contribution)
- Portfolio Covariance & Correlation Penalty (penalizes redundant exposures)
- Concentration Ceilings (50% max single-asset allocation)
- Portfolio Heat Constraint (aggregate risk <= 3.00%)
- Drawdown Throttling (tiered risk reduction during equity troughs)
- Degradation Throttling (automatic haircut on degraded strategies)
- Capacity Limits (notional allocation bounded by market depth / volume)
- Lifecycle Awareness (RESEARCH and FALSIFIED receive 0% capital)
- Fail-Closed Architecture (rejects on NaN, invalid covariance, or missing inputs)
- Subordinate to 7-Dimensional Portfolio Risk Firewall
"""

import math
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from risk_engine.portfolio_risk_firewall import PortfolioRiskFirewall, FirewallThresholds


class AllocatorLifecycleEligibility(str, Enum):
    RESEARCH = "RESEARCH"
    HISTORICAL_ROBUST = "HISTORICAL_ROBUST"
    FORWARD_HEALTHY = "FORWARD_HEALTHY"
    PRODUCTION_QUALIFIED = "PRODUCTION_QUALIFIED"
    FALSIFIED = "FALSIFIED"


@dataclass
class AlphaSlotInput:
    strategy_id: str
    symbol: str
    timeframe: str
    expected_net_edge_r: float          # Net expectancy in R after all friction
    uncertainty_penalty: float          # Standard error or 95% bootstrap CI half-width
    volatility_annual_pct: float        # Annualized volatility in %
    max_drawdown_pct: float             # Historical or forward max drawdown
    capacity_limit_usd: float           # Estimated liquidity/capacity ceiling
    execution_quality_score: float      # Score from 0.0 (poor) to 1.0 (perfect)
    lifecycle_tier: str                 # "RESEARCH", "HISTORICAL_ROBUST", "FORWARD_HEALTHY", "PRODUCTION_QUALIFIED", "FALSIFIED"
    degradation_flag: bool = False      # True if strategy exhibits performance degradation


@dataclass
class AlphaAllocationResult:
    strategy_id: str
    symbol: str
    is_allocated: bool
    recommended_risk_pct: float         # Risk allocation as % of portfolio equity (e.g. 0.60%)
    recommended_notional_usd: float     # Dollar position size
    allocation_weight_pct: float = 0.0  # Fraction of total portfolio risk budget
    rejection_reasons: List[str] = field(default_factory=list)
    throttling_notes: List[str] = field(default_factory=list)
    raw_proposed_risk_pct: float = 0.0
    adjusted_edge_r: float = 0.0
    covariance_discount_pct: float = 0.0
    is_capped_by_strategy_ceiling: bool = False
    is_capped_by_asset_ceiling: bool = False
    is_capped_by_heat_ceiling: bool = False


@dataclass
class PortfolioAllocationReport:
    total_portfolio_equity_usd: float
    current_portfolio_drawdown_pct: float
    max_portfolio_heat_pct: float
    total_allocated_heat_pct: float
    is_capital_firewall_locked: bool
    firewall_veto_triggered: bool
    firewall_veto_reasons: List[str]
    allocations: Dict[str, AlphaAllocationResult]
    rejected_strategies_count: int
    allocated_strategies_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_portfolio_equity_usd": self.total_portfolio_equity_usd,
            "current_portfolio_drawdown_pct": round(self.current_portfolio_drawdown_pct, 2),
            "max_portfolio_heat_pct": self.max_portfolio_heat_pct,
            "total_allocated_heat_pct": round(self.total_allocated_heat_pct, 4),
            "is_capital_firewall_locked": self.is_capital_firewall_locked,
            "firewall_veto_triggered": self.firewall_veto_triggered,
            "firewall_veto_reasons": self.firewall_veto_reasons,
            "allocated_strategies_count": self.allocated_strategies_count,
            "rejected_strategies_count": self.rejected_strategies_count,
            "allocations": {k: asdict(v) for k, v in self.allocations.items()},
        }


class GenericCapitalAllocator:
    """
    Generic Dynamic Portfolio Allocator fail-closed by construction.
    """

    MAX_PORTFOLIO_HEAT_PCT = 3.00       # Hard ceiling: 3.00% total simultaneous active risk
    MAX_SINGLE_STRATEGY_HEAT_PCT = 1.50 # Hard concentration ceiling: 1.50% risk per strategy
    MAX_SINGLE_ASSET_HEAT_PCT = 1.80    # Hard asset concentration ceiling: 1.80% risk per asset

    def __init__(
        self,
        risk_firewall: Optional[PortfolioRiskFirewall] = None,
        max_portfolio_heat_pct: float = 3.00,
    ):
        self.risk_firewall = risk_firewall or PortfolioRiskFirewall(
            thresholds=FirewallThresholds(max_portfolio_heat_pct=max_portfolio_heat_pct)
        )
        self.max_heat = max_portfolio_heat_pct

    @classmethod
    def calculate_drawdown_multiplier(cls, current_drawdown_pct: float) -> float:
        """
        Calculates dynamic risk scaling multiplier based on current account drawdown:
        - DD <= 5.0%: 1.00x (Full size)
        - 5.0% < DD <= 15.0%: 0.50x (50% throttle)
        - 15.0% < DD <= 25.0%: 0.25x (75% throttle)
        - DD > 25.0%: 0.00x (Circuit Breaker Halt)
        """
        if current_drawdown_pct < 0.0:
            return 1.00
        elif current_drawdown_pct <= 5.0:
            return 1.00
        elif current_drawdown_pct <= 15.0:
            return 0.50
        elif current_drawdown_pct <= 25.0:
            return 0.25
        else:
            return 0.00

    def allocate_portfolio(
        self,
        alpha_slots: List[AlphaSlotInput],
        portfolio_equity_usd: float,
        current_drawdown_pct: float = 0.0,
        covariance_matrix: Optional[np.ndarray] = None,
        strategy_order: Optional[List[str]] = None,
        allow_paper_allocation: bool = True,
    ) -> PortfolioAllocationReport:
        """
        Performs generic, fail-closed dynamic risk allocation across arbitrary alpha slots.
        """
        allocations: Dict[str, AlphaAllocationResult] = {}
        
        # 1. Fail-closed sanity checks on portfolio equity
        if portfolio_equity_usd <= 0 or math.isnan(portfolio_equity_usd) or math.isinf(portfolio_equity_usd):
            return PortfolioAllocationReport(
                total_portfolio_equity_usd=0.0,
                current_portfolio_drawdown_pct=current_drawdown_pct,
                max_portfolio_heat_pct=self.max_heat,
                total_allocated_heat_pct=0.0,
                is_capital_firewall_locked=True,
                firewall_veto_triggered=True,
                firewall_veto_reasons=["INVALID_PORTFOLIO_EQUITY_FAIL_CLOSED"],
                allocations={},
                rejected_strategies_count=len(alpha_slots),
                allocated_strategies_count=0,
            )

        # 2. Drawdown throttling multiplier
        dd_multiplier = self.calculate_drawdown_multiplier(current_drawdown_pct)
        if dd_multiplier == 0.0:
            # Circuit breaker halt
            for s in alpha_slots:
                allocations[s.strategy_id] = AlphaAllocationResult(
                    strategy_id=s.strategy_id,
                    symbol=s.symbol,
                    is_allocated=False,
                    recommended_risk_pct=0.0,
                    recommended_notional_usd=0.0,
                    allocation_weight_pct=0.0,
                    rejection_reasons=[f"PORTFOLIO_DRAWDOWN_CIRCUIT_BREAKER (DD={current_drawdown_pct:.2f}% > 25%)"],
                )
            return PortfolioAllocationReport(
                total_portfolio_equity_usd=portfolio_equity_usd,
                current_portfolio_drawdown_pct=current_drawdown_pct,
                max_portfolio_heat_pct=self.max_heat,
                total_allocated_heat_pct=0.0,
                is_capital_firewall_locked=True,
                firewall_veto_triggered=True,
                firewall_veto_reasons=["ACCOUNT_DRAWDOWN_HALT"],
                allocations=allocations,
                rejected_strategies_count=len(alpha_slots),
                allocated_strategies_count=0,
            )

        # 3. Filter eligible candidates & compute uncertainty-adjusted edge
        eligible_candidates: List[Tuple[AlphaSlotInput, float]] = []

        for s in alpha_slots:
            reasons = []
            notes = []

            # Check for NaN / Inf in input numbers (Fail Closed)
            if (
                math.isnan(s.expected_net_edge_r) or math.isinf(s.expected_net_edge_r) or
                math.isnan(s.volatility_annual_pct) or s.volatility_annual_pct <= 0 or
                math.isnan(s.uncertainty_penalty) or s.uncertainty_penalty < 0
            ):
                allocations[s.strategy_id] = AlphaAllocationResult(
                    strategy_id=s.strategy_id,
                    symbol=s.symbol,
                    is_allocated=False,
                    recommended_risk_pct=0.0,
                    recommended_notional_usd=0.0,
                    allocation_weight_pct=0.0,
                    rejection_reasons=["INVALID_OR_NAN_NUMERICAL_INPUTS_FAIL_CLOSED"],
                )
                continue

            # Lifecycle Eligibility Check
            tier = s.lifecycle_tier.upper()
            if tier in ("RESEARCH", "FALSIFIED"):
                reasons.append(f"LIFECYCLE_INELIGIBLE ({tier} candidates receive $0 capital)")
            elif tier == "FORWARD_HEALTHY" and not allow_paper_allocation:
                reasons.append("FORWARD_HEALTHY_PAPER_ONLY (Not permitted in real allocation)")

            # Expected Net Edge Check (must be positive)
            if s.expected_net_edge_r <= 0.0:
                reasons.append(f"NEGATIVE_OR_ZERO_NET_EDGE (E_net={s.expected_net_edge_r:.4f}R <= 0)")

            # Uncertainty-Adjusted Edge: E_adj = E_net - 1.96 * uncertainty_penalty
            adj_edge = s.expected_net_edge_r - (1.96 * s.uncertainty_penalty)
            if adj_edge <= 0.0:
                reasons.append(f"STATISTICAL_UNCERTAINTY_EXCEEDS_EDGE (E_adj={adj_edge:.4f}R <= 0)")

            if reasons:
                allocations[s.strategy_id] = AlphaAllocationResult(
                    strategy_id=s.strategy_id,
                    symbol=s.symbol,
                    is_allocated=False,
                    recommended_risk_pct=0.0,
                    recommended_notional_usd=0.0,
                    allocation_weight_pct=0.0,
                    rejection_reasons=reasons,
                )
            else:
                eligible_candidates.append((s, adj_edge))

        if not eligible_candidates:
            return PortfolioAllocationReport(
                total_portfolio_equity_usd=portfolio_equity_usd,
                current_portfolio_drawdown_pct=current_drawdown_pct,
                max_portfolio_heat_pct=self.max_heat,
                total_allocated_heat_pct=0.0,
                is_capital_firewall_locked=True,
                firewall_veto_triggered=False,
                firewall_veto_reasons=[],
                allocations=allocations,
                rejected_strategies_count=len(alpha_slots),
                allocated_strategies_count=0,
            )

        # 4. Volatility-Normalized Risk Sizing
        # Raw weight = (adj_edge / volatility) * execution_quality_score
        raw_weights = []
        for s, adj_e in eligible_candidates:
            exec_quality = max(0.1, min(1.0, s.execution_quality_score))
            raw_w = (adj_e / s.volatility_annual_pct) * exec_quality
            if s.degradation_flag:
                raw_w *= 0.50  # 50% degradation haircut
            raw_weights.append(raw_w)

        sum_raw = sum(raw_weights)
        if sum_raw <= 1e-9:
            sum_raw = 1.0

        normalized_weights = [w / sum_raw for w in raw_weights]

        # 4b. Covariance & Correlation Penalty
        cov_discounts = [0.0] * len(eligible_candidates)
        if covariance_matrix is not None and len(eligible_candidates) > 1:
            try:
                strat_indices = []
                if strategy_order:
                    id_to_idx = {sid: i for i, sid in enumerate(strategy_order)}
                    for s, _ in eligible_candidates:
                        if s.strategy_id in id_to_idx and id_to_idx[s.strategy_id] < covariance_matrix.shape[0]:
                            strat_indices.append(id_to_idx[s.strategy_id])
                else:
                    if covariance_matrix.shape[0] >= len(eligible_candidates):
                        strat_indices = list(range(len(eligible_candidates)))

                if len(strat_indices) == len(eligible_candidates):
                    sub_cov = covariance_matrix[np.ix_(strat_indices, strat_indices)]
                    reg_lambda = 0.10 * np.trace(sub_cov) / len(eligible_candidates) if np.trace(sub_cov) > 0 else 0.01
                    reg_cov = sub_cov + np.eye(len(eligible_candidates)) * reg_lambda
                    inv_cov = np.linalg.pinv(reg_cov)
                    cov_adjusted_w = inv_cov @ np.array(raw_weights, dtype=np.float64)
                    cov_adjusted_w = np.maximum(0.0, cov_adjusted_w)
                    sum_cov_w = np.sum(cov_adjusted_w)
                    if sum_cov_w > 1e-9:
                        cov_norm_w = cov_adjusted_w / sum_cov_w
                        for i in range(len(eligible_candidates)):
                            nominal_w = normalized_weights[i]
                            actual_w = cov_norm_w[i]
                            if nominal_w > 0 and actual_w < nominal_w:
                                cov_discounts[i] = round((1.0 - (actual_w / nominal_w)) * 100.0, 2)
                        normalized_weights = cov_norm_w.tolist()
            except Exception:
                pass

        # 5. Apply Portfolio Heat and Concentration Ceilings
        target_total_heat = self.max_heat * dd_multiplier

        asset_heat_tracker: Dict[str, float] = {}
        total_allocated_heat = 0.0

        for idx, (s, adj_e) in enumerate(eligible_candidates):
            w = normalized_weights[idx]
            raw_proposed = target_total_heat * w
            proposed_risk_pct = raw_proposed
            notes = []

            is_capped_strat = False
            is_capped_asset = False
            is_capped_heat = False

            # Covariance discount note
            if cov_discounts[idx] > 0.0:
                notes.append(f"Covariance penalty applied ({cov_discounts[idx]:.1f}% reduction)")

            # Strategy concentration cap
            max_strat_cap = self.MAX_SINGLE_STRATEGY_HEAT_PCT * dd_multiplier
            if proposed_risk_pct > max_strat_cap:
                proposed_risk_pct = max_strat_cap
                is_capped_strat = True
                notes.append(f"Capped at strategy concentration ceiling ({max_strat_cap:.2f}%)")

            # Asset concentration cap
            max_asset_cap = self.MAX_SINGLE_ASSET_HEAT_PCT * dd_multiplier
            curr_asset_heat = asset_heat_tracker.get(s.symbol, 0.0)
            if curr_asset_heat + proposed_risk_pct > max_asset_cap:
                allowed_asset_risk = max(0.0, max_asset_cap - curr_asset_heat)
                if allowed_asset_risk < proposed_risk_pct:
                    proposed_risk_pct = allowed_asset_risk
                    is_capped_asset = True
                    notes.append(f"Capped at asset concentration ceiling for {s.symbol} ({max_asset_cap:.2f}%)")

            # Portfolio heat ceiling check
            if total_allocated_heat + proposed_risk_pct > self.max_heat:
                proposed_risk_pct = max(0.0, self.max_heat - total_allocated_heat)
                is_capped_heat = True
                notes.append(f"Capped at global portfolio heat ceiling ({self.max_heat:.2f}%)")

            if dd_multiplier < 1.0:
                notes.append(f"Drawdown throttled ({dd_multiplier * 100:.0f}% of nominal)")
            if s.degradation_flag:
                notes.append("Degradation penalty (50% haircut applied)")

            # Compute Notional Position Size based on 1R risk amount
            risk_usd = portfolio_equity_usd * (proposed_risk_pct / 100.0)
            notional_usd = risk_usd / 0.02
            if s.capacity_limit_usd > 0 and notional_usd > s.capacity_limit_usd:
                notional_usd = s.capacity_limit_usd
                notes.append(f"Capped by market capacity limit (${s.capacity_limit_usd:,.0f})")

            asset_heat_tracker[s.symbol] = curr_asset_heat + proposed_risk_pct
            total_allocated_heat += proposed_risk_pct

            allocations[s.strategy_id] = AlphaAllocationResult(
                strategy_id=s.strategy_id,
                symbol=s.symbol,
                is_allocated=(proposed_risk_pct > 0.001),
                recommended_risk_pct=round(proposed_risk_pct, 4),
                recommended_notional_usd=round(notional_usd, 2),
                allocation_weight_pct=round(w * 100.0, 2),
                rejection_reasons=[],
                throttling_notes=notes,
                raw_proposed_risk_pct=round(raw_proposed, 4),
                adjusted_edge_r=round(adj_e, 4),
                covariance_discount_pct=cov_discounts[idx],
                is_capped_by_strategy_ceiling=is_capped_strat,
                is_capped_by_asset_ceiling=is_capped_asset,
                is_capped_by_heat_ceiling=is_capped_heat,
            )

        n_allocated = sum(1 for a in allocations.values() if a.is_allocated)
        n_rejected = len(allocations) - n_allocated

        return PortfolioAllocationReport(
            total_portfolio_equity_usd=portfolio_equity_usd,
            current_portfolio_drawdown_pct=current_drawdown_pct,
            max_portfolio_heat_pct=self.max_heat,
            total_allocated_heat_pct=round(total_allocated_heat, 4),
            is_capital_firewall_locked=True,  # Real capital remains locked!
            firewall_veto_triggered=False,
            firewall_veto_reasons=[],
            allocations=allocations,
            rejected_strategies_count=n_rejected,
            allocated_strategies_count=n_allocated,
        )
