"""
Product 04 — Research Laboratory: Experiment Engine
Executes controlled A/B research experiments, evaluating hypotheses against preserved baselines with statistical rigor.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from research.experiments.experiment_schema import HypothesisSpec, ExperimentResult


class ExperimentEngine:
    """
    Executes and records rigorous quantitative research experiments.
    """

    @staticmethod
    def load_baseline_results(baseline_path: str = "/home/mrcn2/crypto-platform/scratch/unified_context_matrix_results.json") -> List[Dict[str, Any]]:
        """Loads the certified baseline matrix results."""
        if not os.path.exists(baseline_path):
            raise FileNotFoundError(f"Certified baseline matrix results not found at: {baseline_path}")
        with open(baseline_path, "r") as f:
            return json.load(f)

    @staticmethod
    def compute_aggregate_metrics(streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregates stream-level performance metrics into a holistic portfolio summary."""
        total_trades = sum(s["performance"]["total_trades"] for s in streams)
        wins = sum(s["performance"]["wins"] for s in streams)
        losses = sum(s["performance"]["losses"] for s in streams)
        gross_r = sum(s["performance"]["gross_realized_r"] for s in streams)
        fric_r = sum(s["performance"]["total_friction_r"] for s in streams)
        net_r = sum(s["performance"]["net_realized_r"] for s in streams)
        net_pnl = sum(s["performance"]["net_pnl_usd"] for s in streams)
        
        win_rate_pct = round((wins / total_trades) * 100.0, 2) if total_trades > 0 else None
        expectancy_r = round(net_r / total_trades, 4) if total_trades > 0 else None
        
        # Max drawdown across streams
        max_dd_pct = max(s["performance"]["max_drawdown_pct"] for s in streams) if streams else 0.0

        sample_confidence = "STATISTICALLY_EVALUABLE" if total_trades >= 30 else (
            "PRELIMINARY_SAMPLE" if total_trades >= 10 else "SAMPLE_TOO_SMALL"
        )

        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": win_rate_pct,
            "gross_realized_r": round(gross_r, 4),
            "total_friction_r": round(fric_r, 4),
            "net_realized_r": round(net_r, 4),
            "expectancy_r": expectancy_r,
            "net_pnl_usd": round(net_pnl, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "sample_confidence": sample_confidence
        }

    @staticmethod
    def compare_streams(
        baseline_streams: List[Dict[str, Any]],
        treatment_streams: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Computes stream-by-stream comparative diffs."""
        base_map = {s["stream_id"]: s for s in baseline_streams}
        treat_map = {s["stream_id"]: s for s in treatment_streams}
        
        comparisons = []
        all_sids = sorted(list(set(base_map.keys()) | set(treat_map.keys())))
        
        for sid in all_sids:
            b = base_map.get(sid, {})
            t = treat_map.get(sid, {})
            b_perf = b.get("performance", {})
            t_perf = t.get("performance", {})
            
            b_trades = b_perf.get("total_trades", 0)
            t_trades = t_perf.get("total_trades", 0)
            
            b_net_r = b_perf.get("net_realized_r", 0.0)
            t_net_r = t_perf.get("net_realized_r", 0.0)
            
            b_pnl = b_perf.get("net_pnl_usd", 0.0)
            t_pnl = t_perf.get("net_pnl_usd", 0.0)
            
            comparisons.append({
                "stream_id": sid,
                "baseline_trades": b_trades,
                "treatment_trades": t_trades,
                "delta_trades": t_trades - b_trades,
                "baseline_net_r": b_net_r,
                "treatment_net_r": t_net_r,
                "delta_net_r": round(t_net_r - b_net_r, 4),
                "baseline_net_pnl": b_pnl,
                "treatment_net_pnl": t_pnl,
                "delta_net_pnl": round(t_pnl - b_pnl, 2)
            })
            
        return comparisons

    @staticmethod
    def evaluate_falsification(
        hypothesis: HypothesisSpec,
        baseline_metrics: Dict[str, Any],
        treatment_metrics: Dict[str, Any],
        stream_comparisons: List[Dict[str, Any]]
    ) -> tuple[str, str]:
        """
        Evaluates whether a hypothesis survives or is falsified based on empirical evidence.
        """
        t_trades = treatment_metrics["total_trades"]
        t_net_r = treatment_metrics["net_realized_r"]
        t_exp_r = treatment_metrics["expectancy_r"]
        
        crit = hypothesis.falsification_criteria
        min_trades = crit.get("min_trades", 5)
        min_exp_r = crit.get("min_expectancy_r", -0.10)
        require_better_net_r = crit.get("require_better_net_r", True)
        
        b_net_r = baseline_metrics["net_realized_r"]
        
        if t_trades == 0:
            return "REJECTED", "Treatment generated 0 trades across all streams (mechanism destroys all opportunity generation)."
            
        if require_better_net_r and t_net_r < b_net_r:
            return "REJECTED", f"Treatment degraded net realized R from {b_net_r:+.2f}R to {t_net_r:+.2f}R."
            
        if t_trades < min_trades:
            return "INCONCLUSIVE", f"Sample size ({t_trades} trades) is insufficient for statistical confidence (< {min_trades} required)."
            
        if t_exp_r is not None and t_exp_r < min_exp_r:
            return "REJECTED", f"Treatment expectancy {t_exp_r:+.4f}R failed minimum threshold {min_exp_r:+.4f}R."
            
        return "SURVIVES_FOR_OOS", f"Hypothesis improved net R by {t_net_r - b_net_r:+.2f}R across {t_trades} trades. Qualified for multi-year Out-Of-Sample validation."

    @staticmethod
    def run_experiment(
        hypothesis: HypothesisSpec,
        treatment_streams: List[Dict[str, Any]],
        baseline_path: str = "/home/mrcn2/crypto-platform/scratch/unified_context_matrix_results.json",
        output_dir: str = "/home/mrcn2/crypto-platform/scratch/experiments"
    ) -> ExperimentResult:
        """
        Runs complete A/B experiment analysis against the certified baseline.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        baseline_streams = ExperimentEngine.load_baseline_results(baseline_path)
        baseline_metrics = ExperimentEngine.compute_aggregate_metrics(baseline_streams)
        treatment_metrics = ExperimentEngine.compute_aggregate_metrics(treatment_streams)
        
        # Compute delta metrics
        delta_metrics = {
            "delta_trades": treatment_metrics["total_trades"] - baseline_metrics["total_trades"],
            "delta_wins": treatment_metrics["wins"] - baseline_metrics["wins"],
            "delta_losses": treatment_metrics["losses"] - baseline_metrics["losses"],
            "delta_net_realized_r": round(treatment_metrics["net_realized_r"] - baseline_metrics["net_realized_r"], 4),
            "delta_net_pnl_usd": round(treatment_metrics["net_pnl_usd"] - baseline_metrics["net_pnl_usd"], 2),
            "delta_max_drawdown_pct": round(treatment_metrics["max_drawdown_pct"] - baseline_metrics["max_drawdown_pct"], 2)
        }
        
        stream_comparisons = ExperimentEngine.compare_streams(baseline_streams, treatment_streams)
        decision, reasoning = ExperimentEngine.evaluate_falsification(
            hypothesis, baseline_metrics, treatment_metrics, stream_comparisons
        )
        
        now_utc = datetime.now(timezone.utc).isoformat()
        
        result = ExperimentResult(
            experiment_id=f"EXP_{hypothesis.hypothesis_id}_{int(time.time())}",
            hypothesis_id=hypothesis.hypothesis_id,
            baseline_id=hypothesis.baseline_id,
            variable_under_test=hypothesis.variable_under_test,
            timestamp_utc=now_utc,
            status="COMPLETED",
            decision=decision,
            decision_reasoning=reasoning,
            baseline_metrics=baseline_metrics,
            treatment_metrics=treatment_metrics,
            delta_metrics=delta_metrics,
            stream_level_comparison=stream_comparisons,
            provenance={
                "architecture_standard": "v2.0-UNIFIED-CANONICAL",
                "hierarchy": "Wealth Multiplier Systems -> Quantitative Systems Platform -> Product 01: Crypto Platform"
            }
        )
        
        out_file = os.path.join(output_dir, f"{result.experiment_id}.json")
        with open(out_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
            
        print(f"✅ Experiment result recorded to: {out_file}")
        return result
