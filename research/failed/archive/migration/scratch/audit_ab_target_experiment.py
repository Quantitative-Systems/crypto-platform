"""
Day 41 Forensic Audit: Target Hierarchy A/B Experiment Analysis
Compares Control (COMPOSITE_01 Baseline: CLOSEST_OBJECTIVE)
against Treatment (EXP_TARGET_STRUCTURAL_01: STRUCTURAL_OBJECTIVE)
strictly on 2021-2022 Development Data.
"""

import json
import numpy as np
from collections import Counter
from datetime import datetime, timezone
import os
import sys

def load_results(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing results file: {path}")
    with open(path) as f:
        return json.load(f)

def run_ab_audit():
    baseline_path = "scratch/composite_01_dev_results_repaired_terminal.json"
    exp_path = "scratch/exp_target_structural_01_dev_results.json"
    
    print(f"Loading Baseline Control: {baseline_path}")
    base_data = load_results(baseline_path)
    print(f"Loading Experiment Treatment: {exp_path}")
    exp_data = load_results(exp_path)
    
    # 1. Extract candidate sets
    base_cands_map = {}
    exp_cands_map = {}
    
    for s in base_data.get("stream_results", []):
        sid = s.get("stream_id")
        for c in s.get("all_candidates", []):
            c["stream_id"] = sid
            c["asset"] = s.get("asset")
            c["timeframe_set"] = s.get("timeframe_set")
            base_cands_map[c["candidate_id"]] = c
            
    for s in exp_data.get("stream_results", []):
        sid = s.get("stream_id")
        for c in s.get("all_candidates", []):
            c["stream_id"] = sid
            c["asset"] = s.get("asset")
            c["timeframe_set"] = s.get("timeframe_set")
            exp_cands_map[c["candidate_id"]] = c
            
    print(f"\n--- POPULATION AUDIT ---")
    print(f"Baseline Total Candidates: {len(base_cands_map)}")
    print(f"Experiment Total Candidates: {len(exp_cands_map)}")
    
    # Check candidate identity
    base_ids = set(base_cands_map.keys())
    exp_ids = set(exp_cands_map.keys())
    common_ids = base_ids.intersection(exp_ids)
    print(f"Common Candidate IDs: {len(common_ids)}")
    if len(base_ids) != len(exp_ids) or base_ids != exp_ids:
        print(f"WARNING: Discrepancy in candidate IDs!")
        print(f"  Only in Baseline: {len(base_ids - exp_ids)}")
        print(f"  Only in Experiment: {len(exp_ids - base_ids)}")
    else:
        print(f"VERIFIED: Exact 1-to-1 match of all {len(base_ids)} candidate IDs across 15 streams.")
        
    # 2. Filter for LTF-confirmed triggers (the 391 population)
    base_391 = {cid: c for cid, c in base_cands_map.items() if "RISK_GATE" in c.get("stages_reached", [])}
    exp_391 = {cid: c for cid, c in exp_cands_map.items() if "RISK_GATE" in c.get("stages_reached", [])}
    
    print(f"\n--- SAME-TRIGGER 391 AUDIT ---")
    print(f"Baseline LTF-Confirmed Triggers: {len(base_391)}")
    print(f"Experiment LTF-Confirmed Triggers: {len(exp_391)}")
    
    # 3. Analyze planned RR on the 391 triggers
    base_rrs = []
    exp_rrs = []
    
    base_qual_4r = []
    exp_qual_4r = []
    
    for cid, b_cand in base_391.items():
        e_cand = exp_391.get(cid)
        if not e_cand:
            continue
            
        b_entry = b_cand.get("ltf_entry_price", 0.0)
        b_sl = b_cand.get("ltf_structural_sl", 0.0)
        b_tgt = b_cand.get("htf_target_price")
        
        e_entry = e_cand.get("ltf_entry_price", 0.0)
        e_sl = e_cand.get("ltf_structural_sl", 0.0)
        e_tgt = e_cand.get("htf_target_price")
        
        # Verify frozen entry and stop loss
        assert abs(b_entry - e_entry) < 1e-6, f"Entry mismatch for {cid}: {b_entry} vs {e_entry}"
        assert abs(b_sl - e_sl) < 1e-6, f"SL mismatch for {cid}: {b_sl} vs {e_sl}"
        
        risk = abs(b_entry - b_sl)
        
        if b_tgt is not None and b_tgt > 0.0 and risk > 0:
            b_rr = abs(b_tgt - b_entry) / risk
            base_rrs.append(b_rr)
            if b_rr >= 4.0:
                base_qual_4r.append(cid)
                
        if e_tgt is not None and e_tgt > 0.0 and risk > 0:
            e_rr = abs(e_tgt - e_entry) / risk
            exp_rrs.append(e_rr)
            if e_rr >= 4.0:
                exp_qual_4r.append(cid)

    print(f"\n--- TARGET RESOLUTION & RR STATS ---")
    print(f"Baseline Target Resolved: {len(base_rrs)} / {len(base_391)} ({len(base_rrs)/len(base_391)*100:.2f}%)")
    print(f"Experiment Target Resolved: {len(exp_rrs)} / {len(exp_391)} ({len(exp_rrs)/len(exp_391)*100:.2f}%)")
    
    print(f"\nPlanned RR Distribution (Target Resolved):")
    print(f"Metric              | Baseline (Control) | Experiment (Treatment) | Delta")
    print(f"-------------------------------------------------------------------------")
    print(f"Count               | {len(base_rrs):18d} | {len(exp_rrs):22d} | {len(exp_rrs)-len(base_rrs):+d}")
    print(f"Min RR              | {np.min(base_rrs):17.4f}R | {np.min(exp_rrs):21.4f}R | {np.min(exp_rrs)-np.min(base_rrs):+.4f}R")
    print(f"P25 RR              | {np.percentile(base_rrs, 25):17.4f}R | {np.percentile(exp_rrs, 25):21.4f}R | {np.percentile(exp_rrs, 25)-np.percentile(base_rrs, 25):+.4f}R")
    print(f"Median RR (P50)     | {np.median(base_rrs):17.4f}R | {np.median(exp_rrs):21.4f}R | {np.median(exp_rrs)-np.median(base_rrs):+.4f}R")
    print(f"Mean RR             | {np.mean(base_rrs):17.4f}R | {np.mean(exp_rrs):21.4f}R | {np.mean(exp_rrs)-np.mean(base_rrs):+.4f}R")
    print(f"P75 RR              | {np.percentile(base_rrs, 75):17.4f}R | {np.percentile(exp_rrs, 75):21.4f}R | {np.percentile(exp_rrs, 75)-np.percentile(base_rrs, 75):+.4f}R")
    print(f"P90 RR              | {np.percentile(base_rrs, 90):17.4f}R | {np.percentile(exp_rrs, 90):21.4f}R | {np.percentile(exp_rrs, 90)-np.percentile(base_rrs, 90):+.4f}R")
    print(f"Max RR              | {np.max(base_rrs):17.4f}R | {np.max(exp_rrs):21.4f}R | {np.max(exp_rrs)-np.max(base_rrs):+.4f}R")
    print(f">= 4.0R Qualified   | {len(base_qual_4r):18d} | {len(exp_qual_4r):22d} | {len(exp_qual_4r)-len(base_qual_4r):+d}")
    base_conv = len(base_qual_4r) / len(base_391) * 100
    exp_conv = len(exp_qual_4r) / len(exp_391) * 100
    print(f">= 4.0R Conversion  | {base_conv:17.2f}% | {exp_conv:21.2f}% | {exp_conv-base_conv:+.2f}%")

    # 4. Executed trade metrics
    base_trades = base_data.get("all_trades", [])
    exp_trades = exp_data.get("all_trades", [])
    
    base_perf = base_data.get("aggregate_performance", {})
    exp_perf = exp_data.get("aggregate_performance", {})
    
    print(f"\n--- EXECUTED TRADES PERFORMANCE ---")
    print(f"Metric              | Baseline (Control) | Experiment (Treatment) | Delta")
    print(f"-------------------------------------------------------------------------")
    print(f"Executed Trades     | {len(base_trades):18d} | {len(exp_trades):22d} | {len(exp_trades)-len(base_trades):+d}")
    print(f"Win Rate            | {base_perf.get('win_rate', 0.0):17.2f}% | {exp_perf.get('win_rate', 0.0):21.2f}% | {exp_perf.get('win_rate', 0.0)-base_perf.get('win_rate', 0.0):+.2f}%")
    print(f"Net R               | {base_perf.get('net_r', 0.0):17.4f}R | {exp_perf.get('net_r', 0.0):21.4f}R | {exp_perf.get('net_r', 0.0)-base_perf.get('net_r', 0.0):+.4f}R")
    print(f"Expectancy          | {base_perf.get('expectancy', 0.0):17.4f}R | {exp_perf.get('expectancy', 0.0):21.4f}R | {exp_perf.get('expectancy', 0.0)-base_perf.get('expectancy', 0.0):+.4f}R")
    print(f"Profit Factor       | {base_perf.get('profit_factor', 0.0):18.2f} | {exp_perf.get('profit_factor', 0.0):22.2f} | {exp_perf.get('profit_factor', 0.0)-base_perf.get('profit_factor', 0.0):+.2f}")
    print(f"Max Drawdown (R)    | {base_perf.get('max_drawdown_r', 0.0):17.4f}R | {exp_perf.get('max_drawdown_r', 0.0):21.4f}R | {exp_perf.get('max_drawdown_r', 0.0)-base_perf.get('max_drawdown_r', 0.0):+.4f}R")

    # 5. Target Provenance for newly qualifying >= 4R candidates
    newly_qual = set(exp_qual_4r) - set(base_qual_4r)
    dropped_qual = set(base_qual_4r) - set(exp_qual_4r)
    retained_qual = set(base_qual_4r).intersection(set(exp_qual_4r))
    
    print(f"\n--- QUALIFICATION SHIFTS ---")
    print(f"Retained >= 4R: {len(retained_qual)}")
    print(f"Newly Qualifying >= 4R: {len(newly_qual)}")
    print(f"Dropped < 4R: {len(dropped_qual)}")
    
    # Detail newly qualifying trades
    print(f"\n--- TARGET PROVENANCE FOR NEWLY QUALIFYING SETUPS ---")
    for cid in sorted(newly_qual):
        b = base_391[cid]
        e = exp_391[cid]
        
        b_entry = b.get("ltf_entry_price")
        b_sl = b.get("ltf_structural_sl")
        b_tgt = b.get("htf_target_price")
        b_prov = b.get("htf_target_provenance")
        risk = abs(b_entry - b_sl)
        b_rr = abs(b_tgt - b_entry) / risk if b_tgt else 0.0
        
        e_tgt = e.get("htf_target_price")
        e_prov = e.get("htf_target_provenance")
        e_rr = abs(e_tgt - b_entry) / risk if e_tgt else 0.0
        
        ts = e.get("ltf_confirmation_timestamp", 0)
        dt_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
        
        print(f"\nCandidate: {cid} | Stream: {e.get('stream_id')} | Dir: {e.get('directional_permission')} | Time: {dt_str}")
        print(f"  Entry: {b_entry:.2f} | SL: {b_sl:.2f} (Risk: {risk:.2f})")
        print(f"  Baseline Target: {b_tgt} ({b_prov}) -> Planned RR: {b_rr:.2f}R (< 4R REJECT)")
        print(f"  Experiment Target: {e_tgt} ({e_prov}) -> Planned RR: {e_rr:.2f}R (>= 4R QUALIFIED)")
        print(f"  Provenance Analysis: Target upgraded from {b_prov} to {e_prov}. Expansion factor: {e_rr/b_rr:.2f}x")

if __name__ == "__main__":
    run_ab_audit()
