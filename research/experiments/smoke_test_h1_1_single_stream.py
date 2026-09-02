"""
Product 04 — Research Laboratory: H1.1 Controlled Single-Stream Smoke Test
Executes Section 5 of the Master Directive:
Runs ONE single stream (BTC_SET_3_HYP_B_CONTINUATION_RIDING) under H1.1 rules
to verify candidate generation, trade execution, and wall-clock performance.
"""

import os
import sys
import json
import time
from typing import Dict, Any

from strategy_engine.hypotheses.h1_1_early_mtf_entry import H1_1_EarlyMtfAlignmentEntry
from research.replayer.causal_replayer import CausalReplayer
from research.experiments.run_baseline_002_canonical import load_cached_candles


def run_h1_1_smoke_test() -> Dict[str, Any]:
    symbol = "BTC"
    set_id = "SET_3"
    htf = "1d"
    mtf = "4h"
    ltf = "1h"
    
    print("=" * 80)
    print(f"H1.1 CONTROLLED SMOKE TEST: {symbol}_{set_id}_HYP_B_CONTINUATION_RIDING")
    print("=" * 80)
    
    t0 = time.time()
    htf_candles = load_cached_candles(symbol, htf)
    mtf_candles = load_cached_candles(symbol, mtf)
    ltf_candles = load_cached_candles(symbol, ltf)
    data_load_time = time.time() - t0
    print(f"[DATA] Loaded {len(htf_candles)} {htf}, {len(mtf_candles)} {mtf}, {len(ltf_candles)} {ltf} bars in {round(data_load_time, 2)}s")

    h1_1_hyp = H1_1_EarlyMtfAlignmentEntry()
    
    replayer = CausalReplayer(
        timeframe_set_id=set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=True,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75,
        enable_regime_filter=False,
        cache_htf_mtf=True,
        htf_context_filter="CONTINUATION",
        hypothesis=h1_1_hyp
    )

    t_run = time.time()
    out = replayer.run(
        symbol=f"{symbol}USDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )
    run_time = time.time() - t_run
    
    trades = out.get("closed_trades", [])
    rejected = out.get("rejected_candidates", [])
    funnel = out.get("rejection_funnel", {})
    metrics = out.get("metrics", {})
    
    report = {
        "stream": f"{symbol}_{set_id}_HYP_B_CONTINUATION_RIDING",
        "hypothesis_id": "H1.1_EARLY_MTF_ALIGNMENT_ENTRY",
        "data_load_sec": round(data_load_time, 2),
        "replay_wall_clock_sec": round(run_time, 2),
        "bars_processed": len(ltf_candles),
        "candles_per_sec": round(len(ltf_candles) / run_time, 1) if run_time > 0 else 0.0,
        "total_trades": len(trades),
        "total_rejected": len(rejected),
        "rejection_funnel": funnel,
        "mean_expectancy_r": metrics.get("mean_expectancy_r"),
        "win_rate": metrics.get("win_rate"),
        "net_profit_usd": metrics.get("net_profit_usd"),
        "profit_factor": metrics.get("profit_factor")
    }
    
    print("\n" + "=" * 80)
    print("H1.1 SMOKE TEST RESULT")
    print("=" * 80)
    print(json.dumps(report, indent=2))
    
    out_file = "/home/mrcn2/crypto-platform/scratch/h1_1_smoke_test_result.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
        
    return report


if __name__ == "__main__":
    run_h1_1_smoke_test()
