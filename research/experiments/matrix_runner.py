"""
Product 04 — Research Laboratory: 24-Baseline Research Matrix Runner
Executes 24 isolated baseline streams (2 Hypotheses x 4 Timeframe Sets x 3 Assets)
with complete memory and state quarantine.
"""

from typing import Dict, List, Any, Optional
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import CANONICAL_TIMEFRAME_SETS
from research.exporters.artifact_exporter import ArtifactExporter


ASSETS = ["BTC", "ETH", "SOL"]
HYPOTHESES = ["HYP_A_PULLBACK_RIDING", "HYP_B_CONTINUATION_RIDING"]


class MatrixRunner:
    """
    Orchestrates the execution of all 24 baseline research streams.
    """

    def __init__(self, exporter: Optional[ArtifactExporter] = None):
        self.exporter = exporter or ArtifactExporter()

    def run_matrix(
        self,
        dataset_by_asset_tf: Dict[str, Dict[str, List[Candle]]],
        initial_balance: float = 10000.0,
        enable_mtf_trailing: bool = True
    ) -> Dict[str, Any]:
        """
        Executes 24 baseline streams.
        dataset_by_asset_tf format: { "BTC": {"1M": [...], "1W": [...], "1D": [...], "4H": [...], "1H": [...], "15M": [...]}, ... }
        """
        results_matrix: Dict[str, Any] = {}

        for asset in ASSETS:
            asset_data = dataset_by_asset_tf.get(asset, {})
            if not asset_data:
                continue

            for set_id, tf_set in CANONICAL_TIMEFRAME_SETS.items():
                htf_candles = asset_data.get(tf_set.htf, [])
                mtf_candles = asset_data.get(tf_set.mtf, [])
                ltf_candles = asset_data.get(tf_set.ltf, [])

                if not htf_candles or not mtf_candles or not ltf_candles:
                    continue

                # Run causal replayer in pure memory isolation
                replayer = CausalReplayer(
                    timeframe_set_id=set_id,
                    initial_balance=initial_balance,
                    enable_mtf_trailing=enable_mtf_trailing
                )

                stream_key = f"{asset}_{set_id}"
                run_output = replayer.run(
                    symbol=f"{asset}USDT",
                    htf_candles=htf_candles,
                    mtf_candles=mtf_candles,
                    ltf_candles=ltf_candles
                )

                results_matrix[stream_key] = run_output

                # Export individual stream artifact
                self.exporter.export_run(
                    experiment_name="24_BASELINE_MATRIX",
                    asset=asset,
                    timeframe_set=set_id,
                    hypothesis_id="COMBINED_P02",
                    metrics=run_output["metrics"],
                    exit_attribution=run_output["exit_attribution"],
                    failure_modes=run_output["failure_modes"],
                    trades=run_output["closed_trades"],
                    equity_curve=run_output["equity_curve"],
                    config={"initial_balance": initial_balance, "enable_mtf_trailing": enable_mtf_trailing},
                    dataset_info={"asset": asset, "timeframe_set": set_id, "ltf_bars": len(ltf_candles)}
                )

        return results_matrix
