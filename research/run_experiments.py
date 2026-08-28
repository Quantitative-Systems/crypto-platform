"""
Product 04 — Research Laboratory: Master Baseline Experiment 001 Runner
Executes the complete 24-stream baseline matrix, MTF trailing A/B comparison,
exit attribution, and failure mode analysis without optimization or indicator tampering.
"""

import sys
import os
import json
from typing import Dict, List, Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import CANONICAL_TIMEFRAME_SETS
from research.replayer.causal_replayer import CausalReplayer
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from research.metrics.metrics_engine import MetricsEngine
from research.metrics.exit_attribution import ExitAttributionEngine
from research.analytics.failure_analyzer import FailureAnalyzer
from research.exporters.artifact_exporter import ArtifactExporter
from research.experiments.trailing_ab_experiment import TrailingABExperiment

ASSETS = ["BTC", "ETH", "SOL"]
STRATEGIES = ["HYP_A_PULLBACK_RIDING", "HYP_B_CONTINUATION_RIDING"]


def run():
    print("================================================================================")
    print("      SYSTEM DIRECTIVE: BASELINE EXPERIMENT 001 — FINAL RESEARCH RUN          ")
    print("================================================================================\n")

    # 1. Load Datasets
    print("[1] Loading Multi-Timeframe Historical Warehouse Data...")
    dataset = {}
    timeframes = ["1M", "1W", "1D", "4H", "1H", "15M"]
    for asset in ASSETS:
        dataset[asset] = {}
        for tf in timeframes:
            candles = WarehouseLoader.load_history(f"{asset}/USDT", tf, limit=50000)
            dataset[asset][tf] = candles
            print(f"  • {asset} | {tf}: {len(candles)} candles loaded")

    # 2. Execute 24 Isolated Streams
    print("\n[2] Executing 24-Stream Baseline Matrix (2 Strategies x 4 Sets x 3 Assets)...")
    results_matrix: Dict[str, Any] = {}
    exporter = ArtifactExporter(output_dir=os.path.join(ROOT_DIR, "research", "results"))

    stream_rows = []

    for asset in ASSETS:
        asset_data = dataset[asset]
        for set_id, tf_set in CANONICAL_TIMEFRAME_SETS.items():
            htf_candles = asset_data.get(tf_set.htf, [])
            mtf_candles = asset_data.get(tf_set.mtf, [])
            ltf_candles = asset_data.get(tf_set.ltf, [])

            if not htf_candles or not mtf_candles or not ltf_candles:
                continue

            # Run replayer
            replayer = CausalReplayer(
                timeframe_set_id=set_id,
                initial_balance=10000.0,
                enable_mtf_trailing=True
            )
            raw_output = replayer.run(
                symbol=f"{asset}USDT",
                htf_candles=htf_candles,
                mtf_candles=mtf_candles,
                ltf_candles=ltf_candles
            )

            all_closed = replayer.ledger.closed_trades

            # Decompose into Strategy A (Pullback) and Strategy B (Continuation)
            for strat in STRATEGIES:
                strat_trades = [t for t in all_closed if t.hypothesis_id == strat]
                strat_ledger = TradeLedger(initial_equity=10000.0)
                strat_ledger.closed_trades = strat_trades
                strat_metrics = MetricsEngine.calculate_metrics(strat_trades, strat_ledger)
                strat_exit_attr = ExitAttributionEngine.analyze(strat_trades)
                strat_failures = FailureAnalyzer.classify_failure_modes(strat_trades)

                stream_key = f"{asset}_{set_id}_{'PULLBACK' if 'PULLBACK' in strat else 'CONTINUATION'}"
                stream_data = {
                    "stream_key": stream_key,
                    "asset": asset,
                    "timeframe_set": set_id,
                    "strategy": strat,
                    "metrics": strat_metrics,
                    "exit_attribution": strat_exit_attr,
                    "failure_modes": strat_failures,
                    "trades": [t.to_dict() for t in strat_trades]
                }
                results_matrix[stream_key] = stream_data

                # Export individual stream artifact
                exporter.export_run(
                    experiment_name="BASELINE_001",
                    asset=asset,
                    timeframe_set=set_id,
                    hypothesis_id=strat,
                    metrics=strat_metrics,
                    exit_attribution=strat_exit_attr,
                    failure_modes=strat_failures,
                    trades=stream_data["trades"],
                    equity_curve=strat_ledger.equity_curve,
                    config={"initial_balance": 10000.0, "enable_mtf_trailing": True},
                    dataset_info={"asset": asset, "timeframe_set": set_id, "ltf_bars": len(ltf_candles)}
                )

                stream_rows.append({
                    "stream": stream_key,
                    "trades": strat_metrics["total_trades"],
                    "wins": strat_metrics["win_count"],
                    "losses": strat_metrics["loss_count"],
                    "win_rate": strat_metrics["win_rate"],
                    "exp_r": strat_metrics["expectancy_r"],
                    "avg_r": strat_metrics["average_r"],
                    "profit_factor": strat_metrics["profit_factor"],
                    "max_dd": strat_metrics["max_drawdown_pct"],
                    "net_pnl": strat_metrics["net_profit_usd"],
                    "friction": strat_metrics["total_friction_usd"]
                })

    print(f"  ✅ Completed 24-Stream Baseline Matrix. Processed {len(stream_rows)} isolated streams.")

    # 3. MTF Trailing A/B Comparison
    print("\n[3] Executing MTF Trailing A/B Experiment Across All Sets...")
    ab_runner = TrailingABExperiment()
    ab_results = []
    for asset in ASSETS:
        for set_id, tf_set in CANONICAL_TIMEFRAME_SETS.items():
            htf = dataset[asset][tf_set.htf]
            mtf = dataset[asset][tf_set.mtf]
            ltf = dataset[asset][tf_set.ltf]
            if htf and mtf and ltf:
                res = ab_runner.run_comparison(asset, set_id, htf, mtf, ltf, initial_balance=10000.0)
                ab_results.append(res)

    print("  ✅ Completed Trailing A/B Comparison.")

    # 4. Save Master Summary
    summary_payload = {
        "experiment_name": "BASELINE_EXPERIMENT_001",
        "total_streams": len(stream_rows),
        "streams": results_matrix,
        "trailing_ab_comparison": ab_results
    }
    summary_path = os.path.join(ROOT_DIR, "research", "results", "BASELINE_EXPERIMENT_001_MASTER_SUMMARY.json")
    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary_payload, fp, indent=2, default=str)

    print(f"\n[4] Master Summary Artifact Exported: {summary_path}")

    # 5. Output Summary Table to STDOUT
    print("\n================================================================================")
    print("                     24-STREAM BASELINE PERFORMANCE MATRIX                      ")
    print("================================================================================")
    header = f"{'STREAM':<26} | {'TRADES':<6} | {'W/L':<7} | {'WIN %':<6} | {'EXP (R)':<8} | {'PF':<8} | {'MAX DD %':<8} | {'NET PNL':<10}"
    print(header)
    print("-" * len(header))
    for r in stream_rows:
        wr_str = f"{r['win_rate']*100:.1f}%" if isinstance(r['win_rate'], float) else str(r['win_rate'])
        exp_str = f"{r['exp_r']:.2f}" if isinstance(r['exp_r'], float) else str(r['exp_r'])
        pf_str = f"{r['profit_factor']:.2f}" if isinstance(r['profit_factor'], float) else str(r['profit_factor'])
        dd_str = f"{r['max_dd']*100:.2f}%" if isinstance(r['max_dd'], float) else str(r['max_dd'])
        pnl_str = f"${r['net_pnl']:.2f}" if isinstance(r['net_pnl'], float) else str(r['net_pnl'])
        wl_str = f"{r['wins']}/{r['losses']}"
        print(f"{r['stream']:<26} | {r['trades']:<6} | {wl_str:<7} | {wr_str:<6} | {exp_str:<8} | {pf_str:<8} | {dd_str:<8} | {pnl_str:<10}")

    print("\n================================================================================")
    print("                    MTF TRAILING A/B DELTA COMPARISON                           ")
    print("================================================================================")
    ab_header = f"{'CONFIGURATION':<20} | {'TRADES (A/B)':<12} | {'WR DELTA':<10} | {'EXP (R) DELTA':<14} | {'NET PNL DELTA':<14} | {'MAX DD DELTA':<12}"
    print(ab_header)
    print("-" * len(ab_header))
    for res in ab_results:
        cfg = f"{res['asset']}_{res['timeframe_set']}"
        base_a = res.get("baseline_a_no_trail", res.get("baseline_a_no_trailing", {}))
        base_b = res.get("baseline_b_with_trail", res.get("baseline_b_with_trailing", {}))
        t_a = base_a.get("total_trades", 0)
        t_b = base_b.get("total_trades", 0)
        d = res.get("deltas", {})
        wr_d_val = d.get("win_rate_delta", 0.0)
        wr_d = f"{wr_d_val*100:+.1f}%" if isinstance(wr_d_val, float) else str(wr_d_val)
        exp_d_val = d.get("expectancy_r_delta", 0.0)
        exp_d = f"{exp_d_val:+.2f}R" if isinstance(exp_d_val, float) else str(exp_d_val)
        pnl_d_val = d.get("net_profit_delta_usd", 0.0)
        pnl_d = f"${pnl_d_val:+.2f}" if isinstance(pnl_d_val, float) else str(pnl_d_val)
        dd_d_val = d.get("max_drawdown_delta_pct", 0.0)
        dd_d = f"{dd_d_val*100:+.2f}%" if isinstance(dd_d_val, float) else str(dd_d_val)
        print(f"{cfg:<20} | {f'{t_a}/{t_b}':<12} | {wr_d:<10} | {exp_d:<14} | {pnl_d:<14} | {dd_d:<12}")

    print("\n================================================================================")
    print("                       EXPERIMENT 001 EXECUTION COMPLETE                        ")
    print("================================================================================\n")

if __name__ == "__main__":
    run()
