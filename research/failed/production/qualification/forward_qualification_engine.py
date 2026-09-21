"""
Quantitative Crypto Platform (QCP) — Forward Qualification & Degradation Engine.

Evaluates forward paper execution telemetry against pre-registered research confidence
bounds to detect alpha decay, execution drift, or structural market shifts.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
import math


class QualificationStatus(str, Enum):
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    FORWARD_HEALTHY = "FORWARD_HEALTHY"
    DRIFT_WARNING = "DRIFT_WARNING"
    DEGRADATION_DETECTED = "DEGRADATION_DETECTED"
    QUARANTINED = "QUARANTINED"


@dataclass
class QualificationReport:
    strategy_id: str
    status: QualificationStatus
    total_trades: int
    realized_net_r: float
    realized_expectancy_r: float
    realized_win_rate: float
    realized_max_drawdown_r: float
    expected_expectancy_range: tuple
    expected_win_rate_range: tuple
    drift_score: float                  # Negative indicates adverse degradation
    findings: List[str]
    recommendation: str


class ForwardQualificationEngine:
    """
    Monitors forward paper trades against research benchmarks.
    Detects when a live/paper candidate begins to deteriorate.
    """

    # Empirical benchmark expectations from research
    BENCHMARKS: Dict[str, Dict[str, Any]] = {
        "FAM-07-MTFCONT_SOLUSDT_Set2": {
            "min_eval_trades": 15,
            "expected_exp_r": 0.35,
            "min_exp_r_bound": 0.05,
            "expected_wr": 0.40,
            "min_wr_bound": 0.30,
            "max_allowable_dd_r": 15.0,
            "max_allowable_friction_r": 0.12,
        },
        "FAM-07-MTFCONT_ETHUSDT_Set2": {
            "min_eval_trades": 15,
            "expected_exp_r": 0.20,
            "min_exp_r_bound": 0.00,
            "expected_wr": 0.37,
            "min_wr_bound": 0.28,
            "max_allowable_dd_r": 15.0,
            "max_allowable_friction_r": 0.12,
        },
        "FAM-07-MTFCONT_BTCUSDT_Set2": {
            "min_eval_trades": 15,
            "expected_exp_r": 0.18,
            "min_exp_r_bound": 0.00,
            "expected_wr": 0.36,
            "min_wr_bound": 0.28,
            "max_allowable_dd_r": 15.0,
            "max_allowable_friction_r": 0.12,
        },
    }

    @classmethod
    def evaluate_candidate_telemetry(
        cls,
        strategy_id: str,
        trade_records: List[Dict[str, Any]],
    ) -> QualificationReport:
        """
        Compares list of completed trade dictionaries against strategy benchmarks.
        """
        bm = cls.BENCHMARKS.get(strategy_id, {
            "min_eval_trades": 15,
            "expected_exp_r": 0.15,
            "min_exp_r_bound": 0.02,
            "expected_wr": 0.35,
            "min_wr_bound": 0.25,
            "max_allowable_dd_r": 15.0,
            "max_allowable_friction_r": 0.15,
        })

        n = len(trade_records)
        if n < bm["min_eval_trades"]:
            return QualificationReport(
                strategy_id=strategy_id,
                status=QualificationStatus.INSUFFICIENT_DATA,
                total_trades=n,
                realized_net_r=sum(t.get("net_r", 0.0) for t in trade_records),
                realized_expectancy_r=(sum(t.get("net_r", 0.0) for t in trade_records) / n) if n > 0 else 0.0,
                realized_win_rate=(len([t for t in trade_records if t.get("net_r", 0.0) > 0]) / n) if n > 0 else 0.0,
                realized_max_drawdown_r=0.0,
                expected_expectancy_range=(bm["min_exp_r_bound"], bm["expected_exp_r"]),
                expected_win_rate_range=(bm["min_wr_bound"], bm["expected_wr"]),
                drift_score=0.0,
                findings=[f"Accumulating forward trades: {n}/{bm['min_eval_trades']} trades completed."],
                recommendation="CONTINUE_FORWARD_OBSERVATION",
            )

        # Compute metrics
        net_rs = [t.get("net_r", 0.0) for t in trade_records]
        total_r = sum(net_rs)
        exp_r = total_r / n
        wins = [r for r in net_rs if r > 0]
        wr = len(wins) / n

        # Drawdown calculation
        equity_curve = [0.0]
        for r in net_rs:
            equity_curve.append(equity_curve[-1] + r)
        peak = 0.0
        max_dd = 0.0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd

        findings = []
        status = QualificationStatus.FORWARD_HEALTHY
        recommendation = "PERMIT_CONTINUED_PAPER_TRADING"

        # Check expectancy degradation
        if exp_r < bm["min_exp_r_bound"]:
            findings.append(f"Expectancy degraded: {exp_r:.3f}R below minimum threshold {bm['min_exp_r_bound']:.3f}R.")
            status = QualificationStatus.DEGRADATION_DETECTED
            recommendation = "PAUSE_AND_QUARANTINE"

        # Check win rate degradation
        if wr < bm["min_wr_bound"]:
            findings.append(f"Win rate suppressed: {wr * 100:.1f}% below minimum threshold {bm['min_wr_bound'] * 100:.1f}%.")
            if status != QualificationStatus.DEGRADATION_DETECTED:
                status = QualificationStatus.DRIFT_WARNING
                recommendation = "REDUCE_RISK_BUDGET_50%"

        # Check max drawdown violation
        if max_dd > bm["max_allowable_dd_r"]:
            findings.append(f"Drawdown breach: {max_dd:.2f}R exceeded maximum threshold {bm['max_allowable_dd_r']:.2f}R.")
            status = QualificationStatus.DEGRADATION_DETECTED
            recommendation = "PAUSE_AND_QUARANTINE"

        if not findings:
            findings.append(f"Realized expectancy {exp_r:.3f}R and win rate {wr * 100:.1f}% track within expected confidence bounds.")

        drift_score = (exp_r - bm["expected_exp_r"]) / (bm["expected_exp_r"] if bm["expected_exp_r"] != 0 else 1.0)

        return QualificationReport(
            strategy_id=strategy_id,
            status=status,
            total_trades=n,
            realized_net_r=round(total_r, 4),
            realized_expectancy_r=round(exp_r, 4),
            realized_win_rate=round(wr, 4),
            realized_max_drawdown_r=round(max_dd, 4),
            expected_expectancy_range=(bm["min_exp_r_bound"], bm["expected_exp_r"]),
            expected_win_rate_range=(bm["min_wr_bound"], bm["expected_wr"]),
            drift_score=round(drift_score, 4),
            findings=findings,
            recommendation=recommendation,
        )
