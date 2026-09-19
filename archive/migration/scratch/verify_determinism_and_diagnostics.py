"""
Verify Replay Determinism & Run Comprehensive Baseline Diagnostics for Day 39.
"""
import json
import os
import sys
import hashlib
import numpy as np

sys.path.insert(0, "/home/mrcn2/crypto-platform")

def run_determinism_test():
    print("=" * 80)
    print("PHASE 9: DETERMINISTIC REPLAY VERIFICATION")
    print("=" * 80)
    
    from research.experiments.run_15_stream_canonical_matrix import run_single_stream_canonical
    
    # Run SOL SET_3 twice and compare byte-for-byte trade ledger & performance
    print("Running SOL_SET_3 (Run 1)...")
    res1 = run_single_stream_canonical("SOL", "SET_3")
    print("Running SOL_SET_3 (Run 2)...")
    res2 = run_single_stream_canonical("SOL", "SET_3")
    
    # Compare performance dictionaries
    perf1_json = json.dumps(res1["performance"], sort_keys=True)
    perf2_json = json.dumps(res2["performance"], sort_keys=True)
    
    ledger1_json = json.dumps(res1["trade_ledger"], sort_keys=True)
    ledger2_json = json.dumps(res2["trade_ledger"], sort_keys=True)
    
    perf1_hash = hashlib.sha256(perf1_json.encode()).hexdigest()
    perf2_hash = hashlib.sha256(perf2_json.encode()).hexdigest()
    
    ledger1_hash = hashlib.sha256(ledger1_json.encode()).hexdigest()
    ledger2_hash = hashlib.sha256(ledger2_json.encode()).hexdigest()
    
    print(f"Run 1 Performance SHA256: {perf1_hash}")
    print(f"Run 2 Performance SHA256: {perf2_hash}")
    print(f"Run 1 Trade Ledger SHA256: {ledger1_hash}")
    print(f"Run 2 Trade Ledger SHA256: {ledger2_hash}")
    
    perf_match = (perf1_hash == perf2_hash)
    ledger_match = (ledger1_hash == ledger2_hash)
    
    print(f"Deterministic Performance Match: {'PASSED' if perf_match else 'FAILED'}")
    print(f"Deterministic Ledger Match:      {'PASSED' if ledger_match else 'FAILED'}")
    
    assert perf_match and ledger_match, "Replay is non-deterministic!"
    print(" Deterministic Replay Verification PASSED.")

def analyze_diagnostics():
    print("\n" + "=" * 80)
    print("PHASE 11: FORENSIC DIAGNOSTICS & ATTRIBUTION ANALYSIS")
    print("=" * 80)
    
    matrix_file = "/home/mrcn2/crypto-platform/scratch/canonical_multiyear_matrix_results.json"
    ledger_file = "/home/mrcn2/crypto-platform/scratch/canonical_trade_ledger.json"
    
    with open(matrix_file, "r") as f:
        streams = json.load(f)
        
    trades = []
    if os.path.exists(ledger_file):
        with open(ledger_file, "r") as f:
            raw_ledger = json.load(f)
            if isinstance(raw_ledger, list):
                trades = raw_ledger
            elif isinstance(raw_ledger, dict) and "trades" in raw_ledger:
                trades = raw_ledger["trades"]
    if not trades:
        for s in streams:
            trades.extend(s.get("trade_ledger", []))
        
    # 1. Funnel Rejection Stage Attribution
    print("\n1. LIFECYCLE REJECTION FUNNEL AGGREGATE:")
    funnel_totals = {
        "raw_candles": 0,
        "htf_swings": 0,
        "htf_directional_biases": 0,
        "htf_weak_destinations": 0,
        "candidates_created": 0,
        "mtf_structural_alignments": 0,
        "mtf_keyzones_created": 0,
        "mtf_causal_retests": 0,
        "ltf_triggers": 0,
        "risk_evaluations": 0,
        "risk_approved_plans": 0,
        "submitted_orders": 0,
        "filled_trades": 0,
        "closed_trades": 0
    }
    
    rejection_reasons_global = {}
    for s in streams:
        fn = s["lifecycle_funnel"]
        for k in funnel_totals:
            funnel_totals[k] += fn.get(k, 0)
        for rk, cnt in s["rejection_attribution"].items():
            rejection_reasons_global[rk] = rejection_reasons_global.get(rk, 0) + cnt
            
    for step, cnt in funnel_totals.items():
        print(f"  {step:30s}: {cnt:10d}")
        
    print("\n  Top Rejection Reasons Across All Streams:")
    sorted_rejections = sorted(rejection_reasons_global.items(), key=lambda x: x[1], reverse=True)
    for reason, cnt in sorted_rejections[:10]:
        print(f"    {reason:35s}: {cnt:6d}")
        
    # 2. Exit Reason Breakdown
    print("\n2. EXIT REASON ATTRIBUTION:")
    exit_counts = {}
    for t in trades:
        ex = t["exit_reason"]
        exit_counts[ex] = exit_counts.get(ex, 0) + 1
        
    for ex, cnt in exit_counts.items():
        pct = cnt / len(trades) * 100.0 if trades else 0.0
        sub = [t for t in trades if t["exit_reason"] == ex]
        avg_nr = np.mean([t["realized_r"] for t in sub]) if sub else 0.0
        print(f"  {ex:25s}: {cnt:3d} ({pct:5.1f}%) | Avg Net R: {avg_nr:+6.2f}R")
        
    # 3. Timeframe Set Breakdown
    print("\n3. TIMEFRAME SET DECOMPOSITION:")
    for tf_id in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        sub_s = [s for s in streams if s["identity"]["timeframe_set"] == tf_id]
        tf_trades = sum(s["performance"]["total_trades"] for s in sub_s)
        tf_net_r = sum(s["performance"]["net_realized_r"] for s in sub_s)
        tf_pnl = sum(s["performance"]["net_pnl_usd"] for s in sub_s)
        print(f"  {tf_id:6s} ({sub_s[0]['identity']['label']:15s}): Trades: {tf_trades:2d} | Net R: {tf_net_r:+6.2f}R | Net PnL: ${tf_pnl:+8.2f}")
        
    # 4. Asset Breakdown
    print("\n4. ASSET DECOMPOSITION:")
    for a in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        sub_s = [s for s in streams if a in s["identity"]["asset"] or a.replace("USDT", "/USDT") in s["identity"]["asset"]]
        a_trades = sum(s["performance"]["total_trades"] for s in sub_s)
        a_net_r = sum(s["performance"]["net_realized_r"] for s in sub_s)
        a_pnl = sum(s["performance"]["net_pnl_usd"] for s in sub_s)
        print(f"  {a:10s}: Trades: {a_trades:2d} | Net R: {a_net_r:+6.2f}R | Net PnL: ${a_pnl:+8.2f}")

    # 5. Capital Barrier Verdict Summary
    print("\n5. CAPITAL BARRIER AUDIT VERDICT:")
    verdicts = {}
    for s in streams:
        v = s["performance"]["capital_barrier_verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1
    for v, count in verdicts.items():
        print(f"  {v:30s}: {count:2d} / 15 streams")

if __name__ == "__main__":
    run_determinism_test()
    analyze_diagnostics()
