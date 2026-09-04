"""
Comprehensive Baseline Diagnostics & Forensic Attribution Report for Day 39.
"""
import json
import os
import sys
import numpy as np

def generate_report():
    matrix_file = "/home/mrcn2/crypto-platform/scratch/canonical_multiyear_matrix_results.json"
    
    with open(matrix_file, "r") as f:
        streams = json.load(f)
        
    trades = []
    for s in streams:
        trades.extend(s.get("trade_ledger", []))
        
    print("=" * 100)
    print("DAY 39: CANONICAL 15-STREAM MATRIX BASELINE FORENSIC REPORT")
    print("=" * 100)
    
    # 1. 15-Stream Performance Summary Table
    print("\n1. 15-STREAM MATRIX PERFORMANCE SUMMARY:")
    header = (
        f"| {'Stream':10s} | {'Asset':8s} | {'TF Set':6s} | {'Trades':6s} | {'Win %':6s} | "
        f"{'Gross R':8s} | {'Net R':8s} | {'Exp (R)':8s} | {'PF':5s} | {'Max DD%':7s} | "
        f"{'Max Loss':8s} | {'Avg R':7s} | {'Med R':7s} | {'Barrier Verdict':24s} |"
    )
    print(header)
    print("|" + "-" * 12 + "|" + "-" * 10 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 8 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 10 + "|" + "-" * 7 + "|" + "-" * 9 + "|" + "-" * 10 + "|" + "-" * 9 + "|" + "-" * 9 + "|" + "-" * 26 + "|")
    
    tot_trades = 0
    tot_gross_r = 0.0
    tot_net_r = 0.0
    tot_pnl = 0.0
    
    for s in streams:
        p = s["performance"]
        tot_trades += p["total_trades"]
        tot_gross_r += p["gross_realized_r"]
        tot_net_r += p["net_realized_r"]
        tot_pnl += p["net_pnl_usd"]
        print(
            f"| {s['stream_id']:10s} | {s['identity']['asset']:8s} | {s['identity']['timeframe_set']:6s} | "
            f"{p['total_trades']:6d} | {p['win_rate_pct']:5.1f}% | {p['gross_realized_r']:+7.2f}R | "
            f"{p['net_realized_r']:+7.2f}R | {p['expectancy_r']:+7.3f}R | {p['profit_factor']:5.2f} | "
            f"{p['max_drawdown_pct']:6.1f}% | {p['max_consecutive_losses']:8d} | {p['avg_r']:+6.2f}R | "
            f"{p['median_r']:+6.2f}R | {p['capital_barrier_verdict']:24s} |"
        )
    print("-" * 140)
    print(f"TOTAL TRADES: {tot_trades} | GROSS R: {tot_gross_r:+.2f}R | NET R: {tot_net_r:+.2f}R | NET PNL: ${tot_pnl:+.2f}")
    
    # 2. Lifecycle Funnel Rejection Attribution
    print("\n2. GLOBAL LIFECYCLE FUNNEL METRICS:")
    funnel_totals = {}
    rejections = {}
    for s in streams:
        for k, v in s["lifecycle_funnel"].items():
            funnel_totals[k] = funnel_totals.get(k, 0) + v
        for rk, cnt in s["rejection_attribution"].items():
            rejections[rk] = rejections.get(rk, 0) + cnt
            
    for k, v in funnel_totals.items():
        print(f"  {k:30s}: {v:10d}")
        
    print("\n  Top Rejection Root Causes Across 15 Streams:")
    for r, cnt in sorted(rejections.items(), key=lambda x: x[1], reverse=True):
        print(f"    {r:35s}: {cnt:6d}")
        
    # 3. Exit Reason Distribution
    print("\n3. TRADE EXIT REASON DISTRIBUTION:")
    exit_counts = {}
    for t in trades:
        ex = t.get("exit_reason", "UNKNOWN")
        exit_counts[ex] = exit_counts.get(ex, 0) + 1
    for ex, cnt in exit_counts.items():
        pct = (cnt / len(trades) * 100.0) if trades else 0.0
        sub = [t for t in trades if t.get("exit_reason") == ex]
        avg_r = np.mean([t.get("realized_r", 0.0) for t in sub]) if sub else 0.0
        print(f"  {ex:25s}: {cnt:3d} ({pct:5.1f}%) | Avg Realized R: {avg_r:+6.2f}R")
        
    # 4. Excursion Profile (MAE / MFE)
    mfe_list = []
    mae_list = []
    for s in streams:
        p = s["performance"]
        if p.get("total_trades", 0) > 0:
            mfe_list.append(p.get("avg_mfe_r", 0.0))
            mae_list.append(p.get("avg_mae_r", 0.0))
    print("\n4. EXCURSION PROFILE:")
    print(f"  Average MFE (Max Favorable Excursion): {np.mean(mfe_list):.2f}R")
    print(f"  Average MAE (Max Adverse Excursion):   {np.mean(mae_list):.2f}R")
    
    # 5. Asset & Timeframe Aggregation
    print("\n5. TIME-FRAME SET DECOMPOSITION:")
    for tf_id in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        sub_s = [s for s in streams if s["identity"]["timeframe_set"] == tf_id]
        tr = sum(s["performance"]["total_trades"] for s in sub_s)
        nr = sum(s["performance"]["net_realized_r"] for s in sub_s)
        pnl = sum(s["performance"]["net_pnl_usd"] for s in sub_s)
        lbl = sub_s[0]["identity"]["label"]
        print(f"  {tf_id:6s} ({lbl:32s}): Trades: {tr:2d} | Net R: {nr:+6.2f}R | Net PnL: ${pnl:+8.2f}")
        
    print("\n6. ASSET DECOMPOSITION:")
    for a in ["BTC", "ETH", "SOL"]:
        sub_s = [s for s in streams if a in s["identity"]["asset"]]
        tr = sum(s["performance"]["total_trades"] for s in sub_s)
        nr = sum(s["performance"]["net_realized_r"] for s in sub_s)
        pnl = sum(s["performance"]["net_pnl_usd"] for s in sub_s)
        print(f"  {a:8s}: Trades: {tr:2d} | Net R: {nr:+6.2f}R | Net PnL: ${pnl:+8.2f}")

    print("\n7. CAPITAL BARRIER VERDICT:")
    verdicts = {}
    for s in streams:
        v = s["performance"]["capital_barrier_verdict"]
        verdicts[v] = verdicts.get(v, 0) + 1
    for v, count in verdicts.items():
        print(f"  {v:30s}: {count:2d} / 15 streams")
    print("=" * 100)

if __name__ == "__main__":
    generate_report()
