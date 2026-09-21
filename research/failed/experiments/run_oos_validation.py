"""
Product 04 — Research Laboratory: Out-of-Sample (OOS) & Walk-Forward Validation Framework
Evaluates candidate quantitative hypotheses across temporal partitions, market regimes, and cross-asset transfers.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from research.replayer.timeframe_aligner import TimeframeAligner
from research.replayer.causal_replayer import CausalReplayer
from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from research.simulation.trade_ledger import SimulatedTrade
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.risk_coordinator import RiskCoordinator
from strategy_engine.contracts.strategy_state import CandidateState
from strategy_engine.contracts.trade_plan import DirectionalPermission
from strategy_engine.classifiers.bias_classifier import BiasClassifier
from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext
from strategy_engine.lifecycle.candidate_tracker import CandidateTracker, CandidateSetup
from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy


def analyze_trade_set(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes exact statistical metrics across a collection of trades."""
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "profit_factor": None,
            "net_pnl": 0.0,
            "total_realized_r": 0.0,
            "expectancy_r": 0.0,
            "long_trades": 0,
            "short_trades": 0,
            "exit_attribution": {}
        }

    total = len(trades)
    wins = sum(1 for t in trades if t.get("net_pnl", 0.0) > 0)
    losses = sum(1 for t in trades if t.get("net_pnl", 0.0) <= 0)
    win_rate = (wins / total) * 100.0 if total > 0 else 0.0
    gross_profit = sum(t.get("net_pnl", 0.0) for t in trades if t.get("net_pnl", 0.0) > 0)
    gross_loss = abs(sum(t.get("net_pnl", 0.0) for t in trades if t.get("net_pnl", 0.0) < 0))
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None
    net_pnl = sum(t.get("net_pnl", 0.0) for t in trades)
    total_realized_r = sum(t.get("net_r", 0.0) for t in trades)
    expectancy_r = total_realized_r / total if total > 0 else 0.0
    long_trades = sum(1 for t in trades if "LONG" in str(t.get("directional_permission", "")))
    short_trades = sum(1 for t in trades if "SHORT" in str(t.get("directional_permission", "")))
    exit_attribution: Dict[str, int] = {}
    for t in trades:
        reason = t.get("exit_reason", "UNKNOWN")
        exit_attribution[reason] = exit_attribution.get(reason, 0) + 1

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "net_pnl": net_pnl,
        "total_realized_r": total_realized_r,
        "expectancy_r": expectancy_r,
        "long_trades": long_trades,
        "short_trades": short_trades,
        "exit_attribution": exit_attribution
    }


@dataclass
class ValidationPartition:
    partition_name: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    regime_type: str # BULL_TREND, BEAR_TREND, RANGE_EXPANSION, CHOPPY_CONSOLIDATION


@dataclass
class OOSValidationReport:
    hypothesis_id: str
    in_sample_metrics: Dict[str, Any]
    out_of_sample_metrics: Dict[str, Any]
    walk_forward_ratio: Optional[float]
    cross_asset_results: Dict[str, Any]
    generalization_verdict: str  # ROBUST, OVERFIT, FRAGILE, INSUFFICIENT_SAMPLE


class OOSValidator:
    """
    Coordinates temporal split, walk-forward, and cross-asset validation for quantitative hypotheses.
    """

    TEMPORAL_PARTITIONS = {
        "IS_2021_2022": ValidationPartition("IS_2021_2022", "2021-01-01", "2023-01-01", "BULL_AND_BEAR_CYCLE"),
        "BENCHMARK_2023": ValidationPartition("BENCHMARK_2023", "2023-01-01", "2024-01-01", "ACCUMULATION_RECOVERY"),
        "OOS_2024": ValidationPartition("OOS_2024", "2024-01-01", "2024-08-20", "EXPANSION_BREAKOUT")
    }

    @staticmethod
    def evaluate_generalization(is_exp_r: Optional[float], oos_exp_r: Optional[float], oos_trades: int) -> tuple[Optional[float], str]:
        if oos_trades < 5:
            return None, "INSUFFICIENT_SAMPLE"
        if is_exp_r is None or is_exp_r <= 0:
            return None, "IN_SAMPLE_NOT_PROFITABLE"
        if oos_exp_r is None:
            return 0.0, "OOS_ZERO_TRADES"
            
        wfr = oos_exp_r / is_exp_r
        if wfr >= 0.70:
            return round(wfr, 4), "ROBUST_EDGE"
        elif wfr >= 0.30:
            return round(wfr, 4), "DEGRADED_EDGE"
        else:
            return round(wfr, 4), "OVERFIT_FRAGILE"


def main():
    print("=" * 95)
    print("QUANTITATIVE RESEARCH: OUT-OF-SAMPLE & WALK-FORWARD VALIDATION ENGINE")
    print("=" * 95)
    print("Temporal Partition Framework initialized:")
    for name, p in OOSValidator.TEMPORAL_PARTITIONS.items():
        print(f"  - {name:16s} : {p.start_date} -> {p.end_date} (Regime: {p.regime_type})")
    print("=" * 95)


if __name__ == "__main__":
    main()
