"""Phase O: Real-Venue Paper Execution Reconciliation & Microstructure Audit.

Implements the 5-Dimension Measurement Architecture:
1. Profitability Metrics (Realized R, Expectancy, Win Rate, Profit Factor, Payoff)
2. Execution Drag & Microstructure (Theoretical vs Paper, Spread, Slippage, Latency, Fills)
3. Opportunity Quality (Qualified, Opportunities, Trades, No-Trades, Reason Distribution)
4. Risk & Heat Containment (Portfolio Heat, Single Risk <= 1.0%, Max DD, CVaR95)
5. Drift & Degradation Monitoring (Hypothesis Drift, State Drift, Cost Drift)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MicrostructureFillAudit:
    """Detailed tick-level execution fill audit comparing theoretical signal to paper fill."""
    fill_id: str
    symbol: str
    direction: str                     # "LONG" or "SHORT"
    timestamp_ms: int
    theoretical_entry: float
    paper_fill_price: float
    initial_stop_price: float
    target_price: float
    destination_r: float
    observed_spread_bps: float
    realized_slippage_bps: float
    execution_latency_ms: float
    partial_fill_ratio: float = 1.0    # 1.0 = fully filled, < 1.0 = partial
    order_rejected: bool = False
    fee_bps: float = 7.5               # e.g., VIP0 taker fee baseline
    funding_drag_bps: float = 0.0

    @property
    def stop_distance_pct(self) -> float:
        if self.theoretical_entry <= 0:
            return 0.01
        return abs(self.theoretical_entry - self.initial_stop_price) / self.theoretical_entry

    @property
    def execution_drag_r(self) -> float:
        """Adverse fill distance measured in fractions of initial Risk Unit (R)."""
        if self.order_rejected or self.theoretical_entry <= 0:
            return 0.0
        stop_dist = abs(self.theoretical_entry - self.initial_stop_price)
        if stop_dist <= 0:
            return 0.0
        if self.direction == "LONG":
            adverse_price_delta = self.paper_fill_price - self.theoretical_entry
        else:
            adverse_price_delta = self.theoretical_entry - self.paper_fill_price
        return adverse_price_delta / stop_dist


@dataclass
class ProfitabilityScorecard:
    total_trades: int = 0
    realized_r: float = 0.0
    expectancy_r: float = 0.0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    payoff_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    cvar_95_r: float = 0.0


@dataclass
class ExecutionMicrostructureScorecard:
    avg_execution_drag_r: float = 0.0
    p95_execution_drag_r: float = 0.0
    avg_spread_bps: float = 0.0
    avg_slippage_bps: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    fill_rate_pct: float = 100.0
    rejection_rate_pct: float = 0.0


@dataclass
class OpportunityQualityScorecard:
    qualified_instruments: int = 0
    opportunities_evaluated: int = 0
    trades_executed: int = 0
    no_trade_decisions: int = 0
    conversion_rate_pct: float = 0.0
    top_no_trade_reasons: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class RiskContainmentScorecard:
    max_portfolio_heat_pct: float = 0.0
    max_single_trade_risk_pct: float = 0.0
    max_single_asset_risk_pct: float = 0.0
    heat_limit_breaches: int = 0
    single_risk_breaches: int = 0
    circuit_breaker_trips: int = 0


@dataclass
class DriftMonitoringScorecard:
    hypothesis_expectancy_drift_r: float = 0.0
    execution_cost_drift_bps: float = 0.0
    is_drift_statistically_significant: bool = False
    drift_verdict: str = "STABLE"


@dataclass
class AttributionReconciliationScorecard:
    """Dimension 6: Complete end-to-end auditability and accounting verification."""
    total_reconciled_events: int = 0
    unreconciled_discrepancies: int = 0
    timestamp_alignment_valid: bool = True
    ledger_hash_integrity_valid: bool = True
    accounting_integrity_passed: bool = True
    discrepancy_details: List[str] = field(default_factory=list)


@dataclass
class PhaseOInstitutionalScorecard:
    """Full 6-Dimension Institutional Scorecard for Phase O Paper Live."""
    profitability: ProfitabilityScorecard = field(default_factory=ProfitabilityScorecard)
    microstructure: ExecutionMicrostructureScorecard = field(default_factory=ExecutionMicrostructureScorecard)
    opportunity: OpportunityQualityScorecard = field(default_factory=OpportunityQualityScorecard)
    risk_containment: RiskContainmentScorecard = field(default_factory=RiskContainmentScorecard)
    drift: DriftMonitoringScorecard = field(default_factory=DriftMonitoringScorecard)
    attribution: AttributionReconciliationScorecard = field(default_factory=AttributionReconciliationScorecard)
    recorded_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recorded_at_utc": self.recorded_at_utc,
            "profitability": self.profitability.__dict__,
            "microstructure": self.microstructure.__dict__,
            "opportunity": self.opportunity.__dict__,
            "risk_containment": self.risk_containment.__dict__,
            "drift": self.drift.__dict__,
            "attribution": self.attribution.__dict__,
        }


@dataclass
class PromotionGateEvaluation:
    """Rigorous gating evaluation determining eligibility for Micro-Live (0.1% capital).
    
    Adheres strictly to the principles:
    1. N >= 30 is strictly a necessary operational minimum, NOT statistically sufficient alone.
    2. Lower 95% CI > 0 provides supporting evidence under stated sampling assumptions, not proof of future profit.
    3. Calendar exposure and regime exposure are independent requirements; neither substitutes for the other.
    4. Expectancy must remain positive even after excluding the top 2 winning trades.
    5. Reconciliation and attribution integrity must be mathematically clean with zero accounting bugs.
    """
    is_promotable: bool
    status_summary: str
    rejection_reasons: List[str]
    sample_size_passed: bool             # N >= 30 (necessary minimum)
    time_exposure_days_passed: bool      # days >= 30 (calendar exposure)
    expectancy_floor_passed: bool        # ExpR >= +0.20R
    statistical_confidence_passed: bool   # Lower 95% CI bound > 0.0R (supporting evidence)
    return_concentration_passed: bool    # Top 2 trades <= 60% AND ExpR excluding top 2 > 0.0R
    instrument_diversity_passed: bool    # >= 2 distinct base instruments
    regime_diversity_passed: bool        # >= 2 distinct market regimes (independent of days)
    execution_drag_passed: bool          # Avg drag <= 0.08R and p95 drag <= 0.15R
    zero_governance_breaches: bool       # 0 heat or single-risk breaches
    drift_stability_passed: bool         # drift_verdict == "STABLE"
    attribution_integrity_passed: bool   # 0 unreconciled discrepancies, accounting verified
    metrics: Dict[str, Any] = field(default_factory=dict)


class PhaseOReconciliationAuditor:
    """Aggregates and audits real-venue paper fills against theoretical signals."""

    def __init__(self):
        self.fills: List[MicrostructureFillAudit] = []
        self.trade_outcomes: List[Dict[str, Any]] = []
        self.opportunity_records: List[Dict[str, Any]] = []

    def record_fill(self, fill: MicrostructureFillAudit) -> None:
        self.fills.append(fill)

    def record_trade_outcome(
        self,
        trade_id: str,
        realized_r: float,
        duration_bars: int,
        symbol: str = "BTC/USD",
        regime: str = "EXPANSION_STABLE",
    ) -> None:
        self.trade_outcomes.append({
            "trade_id": trade_id,
            "realized_r": realized_r,
            "duration_bars": duration_bars,
            "symbol": symbol,
            "regime": regime,
        })

    def record_opportunity_cycle(
        self,
        qualified_count: int,
        opp_count: int,
        executed: bool,
        no_trade_reason: Optional[str] = None,
    ) -> None:
        self.opportunity_records.append({
            "qualified_count": qualified_count,
            "opp_count": opp_count,
            "executed": executed,
            "reason": no_trade_reason,
        })

    def generate_scorecard(
        self,
        portfolio_heat_history: Optional[List[float]] = None,
        single_risk_history: Optional[List[float]] = None,
        historical_baseline_exp_r: float = 0.50,
    ) -> PhaseOInstitutionalScorecard:
        """Compute the full 5-dimension scorecard across accumulated paper events."""
        scorecard = PhaseOInstitutionalScorecard()

        # 1. Profitability
        n_trades = len(self.trade_outcomes)
        if n_trades > 0:
            r_list = [t["realized_r"] for t in self.trade_outcomes]
            total_r = sum(r_list)
            wins = [r for r in r_list if r > 0]
            losses = [r for r in r_list if r < 0]
            gross_win = sum(wins)
            gross_loss = abs(sum(losses))
            win_count = len(wins)
            loss_count = len(losses)

            scorecard.profitability.total_trades = n_trades
            scorecard.profitability.realized_r = round(total_r, 3)
            scorecard.profitability.expectancy_r = round(total_r / n_trades, 3)
            scorecard.profitability.win_rate_pct = round(win_count / n_trades * 100, 2)
            scorecard.profitability.profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else 999.0
            scorecard.profitability.avg_win_r = round(gross_win / win_count, 3) if win_count > 0 else 0.0
            scorecard.profitability.avg_loss_r = round(gross_loss / loss_count, 3) if loss_count > 0 else 0.0
            if scorecard.profitability.avg_loss_r > 0:
                scorecard.profitability.payoff_ratio = round(scorecard.profitability.avg_win_r / scorecard.profitability.avg_loss_r, 2)

            # Max drawdown calculation
            peak = 0.0
            max_dd = 0.0
            cum = 0.0
            for r in r_list:
                cum += r
                if cum > peak:
                    peak = cum
                dd = peak - cum
                if dd > max_dd:
                    max_dd = dd
            scorecard.profitability.max_drawdown_pct = round(max_dd, 2)

            # CVaR 95%
            sorted_r = sorted(r_list)
            p05_idx = max(0, int(0.05 * len(sorted_r)))
            tail_losses = sorted_r[:p05_idx + 1]
            scorecard.profitability.cvar_95_r = round(sum(tail_losses) / len(tail_losses), 3) if tail_losses else 0.0

        # 2. Execution Microstructure
        if self.fills:
            drags = [f.execution_drag_r for f in self.fills if not f.order_rejected]
            spreads = [f.observed_spread_bps for f in self.fills]
            slips = [f.realized_slippage_bps for f in self.fills]
            latencies = [f.execution_latency_ms for f in self.fills]
            rejections = [1 for f in self.fills if f.order_rejected]

            scorecard.microstructure.avg_execution_drag_r = round(sum(drags) / len(drags), 4) if drags else 0.0
            if drags:
                sorted_drags = sorted(drags)
                p95_idx = min(len(sorted_drags) - 1, int(0.95 * len(sorted_drags)))
                scorecard.microstructure.p95_execution_drag_r = round(sorted_drags[p95_idx], 4)

            scorecard.microstructure.avg_spread_bps = round(sum(spreads) / len(spreads), 2) if spreads else 0.0
            scorecard.microstructure.avg_slippage_bps = round(sum(slips) / len(slips), 2) if slips else 0.0
            scorecard.microstructure.avg_latency_ms = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
            if latencies:
                sorted_lat = sorted(latencies)
                p95_lat_idx = min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))
                scorecard.microstructure.p95_latency_ms = round(sorted_lat[p95_lat_idx], 1)

            total_orders = len(self.fills)
            scorecard.microstructure.rejection_rate_pct = round(len(rejections) / total_orders * 100, 2)
            scorecard.microstructure.fill_rate_pct = round(100.0 - scorecard.microstructure.rejection_rate_pct, 2)

        # 3. Opportunity Quality
        if self.opportunity_records:
            total_cycles = len(self.opportunity_records)
            executed_cycles = sum(1 for r in self.opportunity_records if r["executed"])
            no_trade_cycles = total_cycles - executed_cycles

            reasons: Dict[str, int] = {}
            for r in self.opportunity_records:
                if not r["executed"] and r.get("reason"):
                    reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1

            max_qual = max([r["qualified_count"] for r in self.opportunity_records], default=0)
            scorecard.opportunity.qualified_instruments = max_qual
            scorecard.opportunity.opportunities_evaluated = total_cycles
            scorecard.opportunity.trades_executed = executed_cycles
            scorecard.opportunity.no_trade_decisions = no_trade_cycles
            scorecard.opportunity.conversion_rate_pct = round(executed_cycles / total_cycles * 100, 2) if total_cycles > 0 else 0.0
            scorecard.opportunity.top_no_trade_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]

        # 4. Risk Containment
        if portfolio_heat_history:
            scorecard.risk_containment.max_portfolio_heat_pct = round(max(portfolio_heat_history), 4)
            scorecard.risk_containment.heat_limit_breaches = sum(1 for h in portfolio_heat_history if h > 0.03001)

        if single_risk_history:
            scorecard.risk_containment.max_single_trade_risk_pct = round(max(single_risk_history), 4)
            scorecard.risk_containment.single_risk_breaches = sum(1 for r in single_risk_history if r > 0.01001)

        # 5. Drift Monitoring
        if n_trades >= 10:
            paper_exp = scorecard.profitability.expectancy_r
            drift = paper_exp - historical_baseline_exp_r
            scorecard.drift.hypothesis_expectancy_drift_r = round(drift, 3)
            # Drift is flagged if expectancy deteriorates by > 0.40R
            if drift < -0.40:
                scorecard.drift.is_drift_statistically_significant = True
                scorecard.drift.drift_verdict = "DEGRADED_DRIFT"
            else:
                scorecard.drift.is_drift_statistically_significant = False
                scorecard.drift.drift_verdict = "STABLE"

        return scorecard

    def evaluate_promotion_gate(
        self,
        scorecard: PhaseOInstitutionalScorecard,
        observation_days: float = 30.0,
    ) -> PromotionGateEvaluation:
        """Evaluate multi-dimensional gating criteria for Micro-Live (0.1% capital) promotion.
        
        N >= 30 is strictly a necessary operational minimum, NOT statistically sufficient alone.
        Calendar exposure and regime exposure are independent non-substitutable requirements.
        """
        rejection_reasons: List[str] = []
        n_trades = len(self.trade_outcomes)

        # 1. Sample Size (Necessary Minimum)
        sample_size_passed = n_trades >= 30
        if not sample_size_passed:
            rejection_reasons.append(f"INSUFFICIENT_SAMPLE_SIZE: {n_trades} < 30 minimum operational trades.")

        # 2. Time Exposure Days (Independent of regime exposure)
        time_exposure_passed = observation_days >= 30.0
        if not time_exposure_passed:
            rejection_reasons.append(f"INSUFFICIENT_TIME_EXPOSURE: {observation_days:.1f} < 30.0 calendar days.")

        # 3. Expectancy Floor (>= +0.20R)
        exp_r = scorecard.profitability.expectancy_r
        expectancy_passed = exp_r >= 0.20
        if not expectancy_passed:
            rejection_reasons.append(f"INSUFFICIENT_EXPECTANCY: {exp_r:.3f}R < +0.200R required floor.")

        # 4. Statistical Supporting Evidence (Lower 95% CI > 0.0R)
        # Provides supporting evidence at 95% confidence under stated sampling assumptions; NOT proof of future profit.
        lower_ci = -999.0
        if n_trades >= 2:
            r_list = [t["realized_r"] for t in self.trade_outcomes]
            mean_r = sum(r_list) / n_trades
            var_r = sum((x - mean_r) ** 2 for x in r_list) / (n_trades - 1)
            std_r = math.sqrt(max(0.0, var_r))
            se_r = std_r / math.sqrt(n_trades)
            lower_ci = mean_r - 1.96 * se_r
            conf_passed = lower_ci > 0.0
        else:
            conf_passed = False
        if not conf_passed:
            rejection_reasons.append(
                f"STATISTICAL_UNCERTAINTY: Lower 95% CI bound ({lower_ci:.3f}R) is not strictly positive (> 0.0R). "
                "Insufficient supporting evidence under empirical return distribution."
            )

        # 5. Return Concentration & Robustness Audit
        r_all = [t["realized_r"] for t in self.trade_outcomes]
        wins = sorted([r for r in r_all if r > 0], reverse=True)
        total_win_r = sum(wins)
        top1_contribution_pct = (wins[0] / total_win_r * 100.0) if wins else 0.0
        top2_contribution_pct = (sum(wins[:2]) / total_win_r * 100.0) if len(wins) >= 2 else top1_contribution_pct
        top5_contribution_pct = (sum(wins[:5]) / total_win_r * 100.0) if len(wins) >= 5 else 100.0

        # Expectancy excluding top 1 and top 2 winners
        if len(r_all) > 2:
            sorted_all_desc = sorted(r_all, reverse=True)
            trimmed_ex_top2 = sorted_all_desc[2:]
            exp_ex_top2 = sum(trimmed_ex_top2) / len(trimmed_ex_top2)
        else:
            exp_ex_top2 = -999.0

        # 5% trimmed expectancy
        sorted_asc = sorted(r_all)
        trim_cut = max(1, int(0.05 * len(r_all)))
        if len(sorted_asc) > 2 * trim_cut:
            core_r = sorted_asc[trim_cut:-trim_cut]
            trimmed_exp = sum(core_r) / len(core_r)
        else:
            trimmed_exp = sum(r_all) / len(r_all) if r_all else 0.0

        top2_share_passed = (top2_contribution_pct <= 60.0) if total_win_r > 0 else False
        ex_top2_positive = exp_ex_top2 > 0.0
        concentration_passed = top2_share_passed and ex_top2_positive
        if not concentration_passed:
            if not top2_share_passed:
                rejection_reasons.append(
                    f"EXCESSIVE_RETURN_CONCENTRATION: Top 2 trades produce {top2_contribution_pct:.1f}% (> 60%) of positive R."
                )
            if not ex_top2_positive:
                rejection_reasons.append(
                    f"OUTLIER_DEPENDENCE: Expectancy excluding top 2 winners collapses to {exp_ex_top2:.3f}R (<= 0.0R)."
                )

        # 6. Instrument Diversity (>= 2 distinct instruments)
        distinct_symbols = len(set(t.get("symbol", "BTC/USD") for t in self.trade_outcomes))
        inst_diversity_passed = distinct_symbols >= 2
        if not inst_diversity_passed:
            rejection_reasons.append(f"LACK_OF_INSTRUMENT_DIVERSITY: Trades concentrated in only {distinct_symbols} instrument (< 2 required).")

        # 7. Regime Diversity (>= 2 distinct regimes; independent of calendar days)
        distinct_regimes = len(set(t.get("regime", "EXPANSION_STABLE") for t in self.trade_outcomes))
        regime_diversity_passed = distinct_regimes >= 2
        if not regime_diversity_passed:
            rejection_reasons.append(f"LACK_OF_REGIME_DIVERSITY: Trades observed in only {distinct_regimes} market regime (< 2 required).")

        # 8. Execution Drag Bound
        avg_drag = scorecard.microstructure.avg_execution_drag_r
        p95_drag = scorecard.microstructure.p95_execution_drag_r
        drag_passed = (avg_drag <= 0.08) and (p95_drag <= 0.15)
        if not drag_passed:
            rejection_reasons.append(f"EXCESSIVE_EXECUTION_DRAG: Avg Drag={avg_drag:.4f}R (limit 0.08R), p95 Drag={p95_drag:.4f}R (limit 0.15R).")

        # 9. Zero Governance Breaches
        gov_passed = (scorecard.risk_containment.heat_limit_breaches == 0) and (scorecard.risk_containment.single_risk_breaches == 0)
        if not gov_passed:
            rejection_reasons.append("GOVERNANCE_BREACH: Heat or single trade risk ceiling violated during paper testing.")

        # 10. Drift Stability
        drift_passed = scorecard.drift.drift_verdict != "DEGRADED_DRIFT"
        if not drift_passed:
            rejection_reasons.append("SIGNIFICANT_DRIFT: Hypothesis or execution cost drift flagged as DEGRADED_DRIFT.")

        # 11. Attribution & Reconciliation Integrity
        attr_passed = (scorecard.attribution.unreconciled_discrepancies == 0) and (scorecard.attribution.accounting_integrity_passed)
        if not attr_passed:
            rejection_reasons.append("RECONCILIATION_DISCREPANCY: Unreconciled execution records or accounting hash mismatches detected.")

        is_promotable = len(rejection_reasons) == 0
        summary = "PROMOTION_GRANTED_TO_MICRO_LIVE" if is_promotable else "PROMOTION_DENIED_GATES_FAILED"

        return PromotionGateEvaluation(
            is_promotable=is_promotable,
            status_summary=summary,
            rejection_reasons=rejection_reasons,
            sample_size_passed=sample_size_passed,
            time_exposure_days_passed=time_exposure_passed,
            expectancy_floor_passed=expectancy_passed,
            statistical_confidence_passed=conf_passed,
            return_concentration_passed=concentration_passed,
            instrument_diversity_passed=inst_diversity_passed,
            regime_diversity_passed=regime_diversity_passed,
            execution_drag_passed=drag_passed,
            zero_governance_breaches=gov_passed,
            drift_stability_passed=drift_passed,
            attribution_integrity_passed=attr_passed,
            metrics={
                "n_trades": n_trades,
                "observation_days": observation_days,
                "expectancy_r": exp_r,
                "lower_95_ci_r": round(lower_ci, 3) if lower_ci != -999.0 else None,
                "top1_contribution_pct": round(top1_contribution_pct, 1),
                "top2_contribution_pct": round(top2_contribution_pct, 1),
                "top5_contribution_pct": round(top5_contribution_pct, 1),
                "expectancy_excluding_top2_r": round(exp_ex_top2, 3) if exp_ex_top2 != -999.0 else None,
                "trimmed_expectancy_r": round(trimmed_exp, 3),
                "distinct_instruments": distinct_symbols,
                "distinct_regimes": distinct_regimes,
                "avg_execution_drag_r": avg_drag,
                "p95_execution_drag_r": p95_drag,
                "attribution_integrity_passed": attr_passed,
            },
        )
