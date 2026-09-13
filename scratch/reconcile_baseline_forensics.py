#!/usr/bin/env python3
"""
Forensic Baseline Reconciliation Script
Compares EXP_TARGET_STRUCTURAL_01 (N=20, +3.83R) vs EXP_BASE_TGTSTRUCT_LEGACY_STOP_01 (N=12, +0.033R).
Evaluates all 15 audit points from the research directive.
"""

import json
import os
import sys

def load_results(path):
    with open(path, "r") as f:
        return json.load(f)

def run_reconciliation():
    path_d1 = "scratch/canonical_exp_target_structural_01_dev_results.json"
    if not os.path.exists(path_d1):
        path_d1 = "scratch/exp_target_structural_01_dev_results.json"
        
    path_d2 = "scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json"

    d1 = load_results(path_d1)
    d2 = load_results(path_d2)

    print("=" * 80)
    print("PHASE 1: BASELINE FORENSIC RECONCILIATION REPORT")
    print("=" * 80)

    # 1. Manifest and Metadata Comparison
    m1 = d1.get("manifest", {})
    m2 = d2.get("manifest", {})
    print(f"\n[MANIFEST]")
    print(f"D1 Experiment ID: {m1.get('experiment_id')}")
    print(f"D1 Git Commit:    {m1.get('git_commit')}")
    print(f"D1 Date:          {m1.get('generated_at_utc')}")
    print(f"D1 Config Hash:   {m1.get('config_hash')}")
    print(f"D2 Experiment ID: {m2.get('experiment_id')}")
    print(f"D2 Git Commit:    {m2.get('git_commit')}")
    print(f"D2 Date:          {m2.get('generated_at_utc')}")
    print(f"D2 Config Hash:   {m2.get('config_hash')}")

    # 2. Performance Overview
    p1 = d1.get("aggregate_performance", {})
    p2 = d2.get("aggregate_performance", {})
    print(f"\n[PERFORMANCE COMPARISON]")
    print(f"{'Metric':25s} | {'D1 (EXP_TARGET_STRUCTURAL_01)':30s} | {'D2 (EXP_BASE_LEGACY_STOP)':25s}")
    print("-" * 85)
    for k in ["total_trades", "wins", "losses", "breakevens", "win_rate", "net_r", "gross_r", "friction_r", "expectancy", "profit_factor", "max_drawdown_r"]:
        print(f"{k:25s} | {str(p1.get(k)):30s} | {str(p2.get(k)):25s}")

    # 3. Trade Inventory & Mapping
    trades1 = d1.get("all_trades", [])
    trades2 = d2.get("all_trades", [])

    # Trade key: (symbol, entry_timestamp, direction)
    t1_map = {(t["symbol"], t["entry_timestamp"], t["direction"]): t for t in trades1}
    t2_map = {(t["symbol"], t["entry_timestamp"], t["direction"]): t for t in trades2}

    common_keys = set(t1_map.keys()) & set(t2_map.keys())
    only_d1_keys = set(t1_map.keys()) - set(t2_map.keys())
    only_d2_keys = set(t2_map.keys()) - set(t1_map.keys())

    print(f"\n[TRADE OVERLAP BREAKDOWN]")
    print(f"Total in D1:        {len(trades1)}")
    print(f"Total in D2:        {len(trades2)}")
    print(f"Common to Both:     {len(common_keys)}")
    print(f"Only in D1:         {len(only_d1_keys)}")
    print(f"Only in D2:         {len(only_d2_keys)}")

    print(f"\n[COMMON TRADES (N={len(common_keys)})]")
    for k in sorted(common_keys):
        t1 = t1_map[k]
        t2 = t2_map[k]
        r1 = t1.get("net_r", 0.0)
        r2 = t2.get("net_r", 0.0)
        exit1 = t1.get("exit_reason", "")
        exit2 = t2.get("exit_reason", "")
        print(f"  {k[0]} {k[2]} @ {k[1]} ({t1.get('stream_id')}): D1_R={r1:+.4f} (exit={exit1}) | D2_R={r2:+.4f} (exit={exit2})")

    print(f"\n[TRADES ONLY IN D1 (N={len(only_d1_keys)})]")
    d1_only_r = 0.0
    for k in sorted(only_d1_keys):
        t = t1_map[k]
        r = t.get("net_r", 0.0)
        d1_only_r += r
        print(f"  {k[0]} {k[2]} @ {k[1]} ({t.get('stream_id')}): Net_R={r:+.4f}, Planned_RR={t.get('raw_rr'):.2f}, Exit={t.get('exit_reason')}, MFE={t.get('mfe_r'):.2f}")
    print(f"Total Net R of D1-only trades: {d1_only_r:+.4f}R")

    print(f"\n[TRADES ONLY IN D2 (N={len(only_d2_keys)})]")
    d2_only_r = 0.0
    for k in sorted(only_d2_keys):
        t = t2_map[k]
        r = t.get("net_r", 0.0)
        d2_only_r += r
        print(f"  {k[0]} {k[2]} @ {k[1]} ({t.get('stream_id')}): Net_R={r:+.4f}, Planned_RR={t.get('raw_rr'):.2f}, Exit={t.get('exit_reason')}, MFE={t.get('mfe_r'):.2f}")
    print(f"Total Net R of D2-only trades: {d2_only_r:+.4f}R")

    # 4. Stream-by-Stream Trade Counts
    print(f"\n[STREAM DISTRIBUTION]")
    streams = set([t.get("stream_id") for t in trades1] + [t.get("stream_id") for t in trades2])
    for s in sorted(streams):
        n1 = sum(1 for t in trades1 if t.get("stream_id") == s)
        n2 = sum(1 for t in trades2 if t.get("stream_id") == s)
        r1 = sum(t.get("net_r", 0.0) for t in trades1 if t.get("stream_id") == s)
        r2 = sum(t.get("net_r", 0.0) for t in trades2 if t.get("stream_id") == s)
        print(f"  {s:12s}: D1 N={n1:2d} ({r1:+7.3f}R) | D2 N={n2:2d} ({r2:+7.3f}R)")

if __name__ == "__main__":
    run_reconciliation()
