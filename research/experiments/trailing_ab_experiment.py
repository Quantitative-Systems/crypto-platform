"""
Product 04 — Research Laboratory: MTF Trailing A/B Experiment Runner
Directly compares Baseline A (Fixed HTF TP + Initial SL, No Trailing)
vs Baseline B (With MTF Structural Trailing) under identical data and friction conditions.
"""

from typing import Dict, List, Any, Optional
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer
from research.exporters.artifact_exporter import ArtifactExporter


class TrailingABExperiment:
    """
    Executes controlled A/B test of the MTF Structural Trailing hypothesis.
    """

    def __init__(self, exporter: Optional[ArtifactExporter] = None):
        self.exporter = exporter or ArtifactExporter()

    def run_comparison(
        self,
        asset: str,
        timeframe_set_id: str,
        htf_candles: List[Candle],
        mtf_candles: List[Candle],
        ltf_candles: List[Candle],
        initial_balance: float = 10000.0
    ) -> Dict[str, Any]:
        
        # 1. Run Baseline A: No MTF Trailing
        replayer_a = CausalReplayer(
            timeframe_set_id=timeframe_set_id,
            initial_balance=initial_balance,
            enable_mtf_trailing=False
        )
        result_a = replayer_a.run(
            symbol=f"{asset}USDT",
            htf_candles=htf_candles,
            mtf_candles=mtf_candles,
            ltf_candles=ltf_candles
        )

        # 2. Run Baseline B: With MTF Trailing
        replayer_b = CausalReplayer(
            timeframe_set_id=timeframe_set_id,
            initial_balance=initial_balance,
            enable_mtf_trailing=True
        )
        result_b = replayer_b.run(
            symbol=f"{asset}USDT",
            htf_candles=htf_candles,
            mtf_candles=mtf_candles,
            ltf_candles=ltf_candles
        )

        # 3. Compute Delta Comparison safely with potential None values on zero-trade streams
        metrics_a = result_a["metrics"]
        metrics_b = result_b["metrics"]

        wr_a = metrics_a.get("win_rate")
        wr_b = metrics_b.get("win_rate")
        wr_delta = round(wr_b - wr_a, 4) if (wr_a is not None and wr_b is not None) else None

        np_a = metrics_a.get("net_profit_usd") if metrics_a.get("net_profit_usd") is not None else 0.0
        np_b = metrics_b.get("net_profit_usd") if metrics_b.get("net_profit_usd") is not None else 0.0
        np_delta = round(np_b - np_a, 2)

        dd_a = metrics_a.get("max_drawdown_pct") if metrics_a.get("max_drawdown_pct") is not None else 0.0
        dd_b = metrics_b.get("max_drawdown_pct") if metrics_b.get("max_drawdown_pct") is not None else 0.0
        dd_delta = round(dd_b - dd_a, 4)

        delta_report = {
            "asset": asset,
            "timeframe_set": timeframe_set_id,
            "baseline_a_no_trail": {
                "total_trades": metrics_a["total_trades"],
                "win_rate": metrics_a["win_rate"],
                "net_profit_usd": metrics_a["net_profit_usd"],
                "profit_factor": metrics_a["profit_factor"],
                "expectancy_r": metrics_a["expectancy_r"],
                "max_drawdown_pct": metrics_a["max_drawdown_pct"],
                "exit_attribution": result_a["exit_attribution"]
            },
            "baseline_b_with_trail": {
                "total_trades": metrics_b["total_trades"],
                "win_rate": metrics_b["win_rate"],
                "net_profit_usd": metrics_b["net_profit_usd"],
                "profit_factor": metrics_b["profit_factor"],
                "expectancy_r": metrics_b["expectancy_r"],
                "max_drawdown_pct": metrics_b["max_drawdown_pct"],
                "exit_attribution": result_b["exit_attribution"]
            },
            "deltas": {
                "win_rate_delta": wr_delta,
                "net_profit_delta_usd": np_delta,
                "max_drawdown_delta_pct": dd_delta
            }
        }

        # Export A/B report
        self.exporter.export_run(
            experiment_name="TRAILING_AB_EXPERIMENT",
            asset=asset,
            timeframe_set=timeframe_set_id,
            hypothesis_id="AB_COMPARISON",
            metrics={"baseline_a": metrics_a, "baseline_b": metrics_b, "deltas": delta_report["deltas"]},
            exit_attribution={"baseline_a": result_a["exit_attribution"], "baseline_b": result_b["exit_attribution"]},
            failure_modes={"baseline_a": result_a["failure_modes"], "baseline_b": result_b["failure_modes"]},
            trades=[],
            equity_curve=[],
            config={"initial_balance": initial_balance},
            dataset_info={"asset": asset, "timeframe_set": timeframe_set_id, "bars": len(ltf_candles)}
        )

        return delta_report
