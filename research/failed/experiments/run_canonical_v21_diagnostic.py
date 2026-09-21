import os
import sys
import json
import time
from collections import Counter
from typing import Dict, Any, List

import pandas as pd
import numpy as np

# Add repo root to sys.path
REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import research.bias_families as bf
import research.setup_families as sf
import research.entry_families as ef
import research.sl_families as slf
import research.tp_families as tpf
import research.trailing_families as trf
from research.grammar_components import ComponentRegistry
from research.strategy_grammar import HypothesisBuilder, TimeframeSet
from research.economic_evaluation_engine import EconomicEvaluationEngine
from platform_core.alpha_genome import AlphaGenome

# Ensure all components are registered
bf.register_all_biases(ComponentRegistry)
sf.register_all_setups(ComponentRegistry)
ef.register_all_entries(ComponentRegistry)
slf.register_all_stop_losses(ComponentRegistry)
tpf.register_all_take_profits(ComponentRegistry)
trf.register_all_trailings(ComponentRegistry)

RESULTS_DIR = os.path.join(REPO_ROOT, "research", "results")

# Constants
ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TF_SETS = {
    "SET_1": (TimeframeSet.SET_1_MACRO, "1d"),
    "SET_2": (TimeframeSet.SET_2_CORE, "4h"),
    "SET_3": (TimeframeSet.SET_3_SWING, "1h"),
    "SET_4": (TimeframeSet.SET_4_INTRADAY, "15m"),
    "SET_5": (TimeframeSet.SET_5_ACTIVE, "5m"),
}

def load_canonical_baseline() -> Dict:
    path = os.path.join(REPO_ROOT, "scratch", "canonical_h0_dev_results.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def run_phase_1():
    print("=" * 80)
    print("PHASE 1: FRAMEWORK REGRESSION / REPRODUCTION")
    print("=" * 80)
    
    baseline = load_canonical_baseline()
    
    engine = EconomicEvaluationEngine(min_trades_per_partition=1)
    
    # We will test over DEV partition 2021-2022
    partitions = [("DEV", "2021-01-01", "2022-12-31")]
    
    results = []
    
    # For Phase 1, we must reproduce all 5 timeframe sets
    for set_id, (tf_set, tf_str) in TF_SETS.items():
        for asset in ASSETS:
            print(f"Running {asset} {tf_str} ({set_id})...")
            genome = AlphaGenome(
                alpha_id=f"CANONICAL_V21_{set_id}_{asset.replace('/', '')}",
                family="DIRECTIONAL",
                version="2.1",
                asset_universe=[asset],
                venues=["Binance"],
                instruments=["SPOT"],
                timeframe=tf_str,
                expected_holding_period_hours=24.0,
                economic_rationale="Trend continuation pullback",
                features=["supertrend", "stochastic"],
                entry_mechanism="canonical_pullback",
                exit_mechanism="dynamic_r_or_ltf_swing"
            )
            
            # Using CANONICAL components
            signal_fn = HypothesisBuilder.build_signal(
                hypothesis_id="CANONICAL",
                bias_id="CANONICAL_SUPERTREND_STOCHASTIC",
                setup_id="CANONICAL_SUPERTREND_STOCHASTIC_SETUP",
                entry_id="CANONICAL_SUPERTREND_STOCHASTIC_ENTRY",
                sl_id="SL_LTF_SWING",
                # 2. HTF Structural Take Profit
                tp_id="TP_HTF_STRUCTURAL",
                # 3. MTF Structural Trailing
                trailing_id="TRAIL_MTF_STRUCTURAL",
                tf_set=tf_set
            )
            
            try:
                res = engine.evaluate(
                    genome=genome,
                    signal_fn=signal_fn,
                    symbol=asset,
                    timeframe=tf_str,
                    partitions=partitions
                )
                results.append(res)
            except Exception as e:
                print(f"Error evaluating {asset} {tf_str}: {e}")
                
    # Quick aggregation for Phase 1
    total_trades = 0
    total_net_r = 0.0
    wins = 0
    
    for r in results:
        if r.overall:
            total_trades += r.overall.trade_count
            total_net_r += r.overall.performance.net_edge_r * r.overall.performance.trade_count # Approximation if net_edge_r is average
            # Actually overall.net_edge_r is the average expectancy.
            
    print(f"\nPhase 1 Result:")
    print(f"Total Trades Evaluated: {total_trades}")
    print(f"If this does not match canonical_h0_dev_results.json, we must abort.")
    
    if baseline:
        b_trades = len(baseline.get("all_trades", [])) # actually wait, baseline.get('aggregate_performance',{}).get('total_trades',0)
        print(f"Baseline Trades: {baseline.get('aggregate_performance', {}).get('total_trades', 0)}")
        
    out_path = os.path.join(REPO_ROOT, "scratch", "v21_diagnostic_results.json")
    out_data = {"stream_results": []}
    for r in results:
        if r.overall:
            stream_data = {
                "stream_id": r.alpha_id,
                "trades": [t.__dict__ for t in r.trades] if r.trades else []
            }
            out_data["stream_results"].append(stream_data)
            
    with open(out_path, "w") as f:
        json.dump(out_data, f, default=str, indent=2)
    print(f"Wrote to {out_path}")
        
    return results

if __name__ == "__main__":
    run_phase_1()
