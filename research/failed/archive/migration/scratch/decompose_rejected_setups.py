"""
Forensic Decomposition of the 354/387 Setups Still Rejected by 4R Firewall
Under EXP_TARGET_STRUCTURAL_01 (Day 41 Observational Analysis)
"""

import json
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timezone
import os, sys

sys.path.insert(0, "/home/mrcn2/crypto-platform")
from market_data.warehouse_loader import WarehouseLoader

def run_decomposition():
    results_path = "scratch/exp_target_structural_01_dev_results.json"
    with open(results_path) as f:
        data = json.load(f)

    # 1. Extract the 354 rejected candidates
    all_cands = []
    for s in data.get("stream_results", []):
        sid = s.get("stream_id")
        asset = s.get("asset")
        tf_set = s.get("timeframe_set")
        for c in s.get("all_candidates", []):
            if "RISK_GATE" in c.get("stages_reached", []) and c.get("invalidation_reason") == "REJECT_RR_BELOW_4R":
                c["stream_id"] = sid
                c["asset"] = asset
                c["tf_set"] = tf_set
                all_cands.append(c)

    print(f"Total Still-Rejected Candidates: {len(all_cands)}")

    # 2. Pre-load candle cache for exact price and timing analysis
    TF_MAP = {"SET_1": "1d", "SET_2": "4h", "SET_3": "1h", "SET_4": "15m"}
    candle_cache = {}
    for asset in ["BTC", "ETH", "SOL"]:
        sym = f"{asset}/USDT"
        for tf_set, tf in TF_MAP.items():
            try:
                cdls = WarehouseLoader.load_history(sym, tf, limit=1_000_000, start_time_ms=None, end_time_ms=1672531199000)
                candle_cache[(sym, tf)] = {c.timestamp: c for c in cdls}
            except Exception as e:
                print(f"Warning loading {sym} {tf}: {e}")

    # 3. Compute detailed geometric metrics for every setup
    enriched_cands = []
    for c in all_cands:
        sym = f"{c['asset']}/USDT"
        tf = TF_MAP.get(c["tf_set"])
        ep = c.get("ltf_entry_price", 0.0)
        sl = c.get("ltf_structural_sl", 0.0)
        tp = c.get("htf_target_price", 0.0)
        risk = abs(ep - sl)
        reward = abs(tp - ep)
        span = abs(tp - sl)
        rr = reward / risk if risk > 0 else 0.0
        
        is_long = ("BULLISH" in str(c.get("htf_macro_direction")) or "LONG" in str(c.get("directional_permission", "")))
        
        # Proportions
        risk_pct = (risk / ep * 100.0) if ep > 0 else 0.0
        reward_pct = (reward / ep * 100.0) if ep > 0 else 0.0
        span_pct = (span / ep * 100.0) if ep > 0 else 0.0
        span_progress = (risk / span * 100.0) if span > 0 else 100.0

        # Timing & Latency
        i_ts = c.get("htf_interaction_timestamp") or c.get("htf_context_timestamp") or 0
        c_ts = c.get("ltf_confirmation_timestamp") or 0
        latency_sec = max(0, c_ts - i_ts)
        latency_hours = latency_sec / 3600.0
        
        # Interaction candle price
        cdls = candle_cache.get((sym, tf), {})
        i_cdl = cdls.get(i_ts)
        c_cdl = cdls.get(c_ts)
        p_i = i_cdl.close if i_cdl else ep
        
        # Price drift from interaction to entry
        drift = (ep - p_i) if is_long else (p_i - ep)
        drift_pct = (abs(drift) / ep * 100.0) if ep > 0 else 0.0
        initial_reward = abs(tp - p_i)
        drift_share_of_target = (drift / initial_reward * 100.0) if (initial_reward > 0 and drift > 0) else 0.0

        c_year = datetime.fromtimestamp(c_ts, tz=timezone.utc).year if c_ts else 2021

        enriched = {
            "cand": c,
            "cid": c.get("candidate_id"),
            "asset": c.get("asset"),
            "tf_set": c.get("tf_set"),
            "year": c_year,
            "dir": "LONG" if is_long else "SHORT",
            "ep": ep,
            "sl": sl,
            "tp": tp,
            "risk": risk,
            "reward": reward,
            "span": span,
            "rr": rr,
            "risk_pct": risk_pct,
            "reward_pct": reward_pct,
            "span_pct": span_pct,
            "span_progress": span_progress,
            "prov": c.get("htf_target_provenance", "UNKNOWN"),
            "latency_hours": latency_hours,
            "p_i": p_i,
            "drift": drift,
            "drift_pct": drift_pct,
            "drift_share_of_target": drift_share_of_target,
            "i_ts": i_ts,
            "c_ts": c_ts
        }
        enriched_cands.append(enriched)

    # 4. Mutually interpretable classification rules
    # Priority classification:
    # 1. Target Ambiguous: provenance is FORWARD_STRUCTURAL_EXPANSION
    # 2. Genuine Wide Stop: stop distance >= 15% (macro sequence invalidation)
    # 3. Proximity to Target: reward_pct < 2.5% (setup spawned right next to target)
    # 4. Confirmation Latency Consumed Range: latency > 4h and drift consumed >= 35% of initial target distance
    # 5. Late Expansion Entry: span_progress >= 65% (entered after 65% of structural move was completed)
    # 6. Healthy Swing Sub-4R: rr >= 1.5R with legitimate target (reward_pct >= 6%)
    # 7. Range Compression / Intermediate Sub-4R: remaining setups where span is modest (< 12%) and entry is 35-65% into range

    categories = {
        "CAT_1_LATE_EXPANSION_ENTRY": [],
        "CAT_2_GENUINE_WIDE_STOP": [],
        "CAT_3_HEALTHY_SWING_SUB_4R": [],
        "CAT_4_TARGET_AMBIGUOUS_EXPANSION": [],
        "CAT_5_CONFIRMATION_LATENCY_CONSUMPTION": [],
        "CAT_6_PROXIMITY_TO_TARGET": [],
        "CAT_7_RANGE_COMPRESSION_MODEST_ROOM": [],
    }

    for e in enriched_cands:
        # Rule 1: Target Ambiguous (Fallback Expansion)
        if e["prov"] == "FORWARD_STRUCTURAL_EXPANSION":
            categories["CAT_4_TARGET_AMBIGUOUS_EXPANSION"].append(e)
        # Rule 2: Genuine Wide Stop (Stop >= 15% or SET_1/SET_2 macro anchor)
        elif e["risk_pct"] >= 15.0 or (e["tf_set"] in ["SET_1", "SET_2"] and e["risk_pct"] >= 12.0):
            categories["CAT_2_GENUINE_WIDE_STOP"].append(e)
        # Rule 3: Proximity to Target (less than 2.5% reward room from entry)
        elif e["reward_pct"] < 2.5:
            categories["CAT_6_PROXIMITY_TO_TARGET"].append(e)
        # Rule 4: Confirmation Latency Consumed Range (latency > 4h and drift ate >= 35% of initial target distance)
        elif e["drift_share_of_target"] >= 35.0 and e["latency_hours"] >= 4.0:
            categories["CAT_5_CONFIRMATION_LATENCY_CONSUMPTION"].append(e)
        # Rule 5: Healthy Swing Sub-4R (RR >= 1.5R and healthy reward >= 5%)
        elif e["rr"] >= 1.50 and e["reward_pct"] >= 5.0:
            categories["CAT_3_HEALTHY_SWING_SUB_4R"].append(e)
        # Rule 6: Late Expansion Entry (price already consumed >= 60% of span)
        elif e["span_progress"] >= 60.0:
            categories["CAT_1_LATE_EXPANSION_ENTRY"].append(e)
        # Rule 7: Range Compression / Modest Dealing Range
        else:
            categories["CAT_7_RANGE_COMPRESSION_MODEST_ROOM"].append(e)

    total = len(enriched_cands)
    print("\n=========================================================================================")
    print("FORENSIC DECOMPOSITION SUMMARY (354 STILL-REJECTED SETUPS)")
    print("=========================================================================================")
    
    cat_names = {
        "CAT_1_LATE_EXPANSION_ENTRY": "1. Late Expansion Entry (>60% of structural span already consumed)",
        "CAT_2_GENUINE_WIDE_STOP": "2. Structurally Necessary Wide Stop (invalidation >= 15% of price)",
        "CAT_3_HEALTHY_SWING_SUB_4R": "3. Healthy Swing Sub-4R (1.5R <= RR < 4.0R, genuine structural target)",
        "CAT_4_TARGET_AMBIGUOUS_EXPANSION": "4. Target Selection Ambiguous (fallback Dealing Range Expansion)",
        "CAT_5_CONFIRMATION_LATENCY_CONSUMPTION": "5. Confirmation Latency Consumed Range (multi-TF drift ate >=35% room)",
        "CAT_6_PROXIMITY_TO_TARGET": "6. Setup Formed in Extreme Proximity to Target (reward room < 2.5%)",
        "CAT_7_RANGE_COMPRESSION_MODEST_ROOM": "7. Dealing Range Compression / Modest Room (span < 12%, RR < 1.5R)",
    }

    for cat_key in [
        "CAT_1_LATE_EXPANSION_ENTRY",
        "CAT_2_GENUINE_WIDE_STOP",
        "CAT_3_HEALTHY_SWING_SUB_4R",
        "CAT_4_TARGET_AMBIGUOUS_EXPANSION",
        "CAT_5_CONFIRMATION_LATENCY_CONSUMPTION",
        "CAT_6_PROXIMITY_TO_TARGET",
        "CAT_7_RANGE_COMPRESSION_MODEST_ROOM"
    ]:
        items = categories[cat_key]
        cnt = len(items)
        pct = cnt / total * 100.0
        rrs = [x["rr"] for x in items] if items else [0]
        rewards = [x["reward_pct"] for x in items] if items else [0]
        stops = [x["risk_pct"] for x in items] if items else [0]
        latencies = [x["latency_hours"] for x in items] if items else [0]
        assets = Counter(x["asset"] for x in items)
        tf_sets = Counter(x["tf_set"] for x in items)
        years = Counter(x["year"] for x in items)
        provs = Counter(x["prov"] for x in items)
        
        print(f"\n-----------------------------------------------------------------------------------------")
        print(f"{cat_names[cat_key]}")
        print(f"  Count: {cnt} ({pct:.2f}%)")
        print(f"  Planned RR:       median={np.median(rrs):.2f}R | mean={np.mean(rrs):.2f}R | range=[{np.min(rrs):.2f}R, {np.max(rrs):.2f}R]")
        print(f"  Target Distance:  median={np.median(rewards):.2f}% | mean={np.mean(rewards):.2f}%")
        print(f"  Stop Distance:    median={np.median(stops):.2f}% | mean={np.mean(stops):.2f}%")
        print(f"  Latency (hours):  median={np.median(latencies):.1f}h | mean={np.mean(latencies):.1f}h")
        print(f"  Assets:           {dict(assets)}")
        print(f"  Timeframe Sets:   {dict(tf_sets)}")
        print(f"  Years:            {dict(years)}")
        print(f"  Target Prov:      {dict(provs)}")
        
        # Print 2 representative examples
        if items:
            print("  Representative Examples:")
            for ex in items[:2]:
                print(f"    - ID: {ex['cid']} | {ex['asset']} {ex['tf_set']} {ex['dir']} ({ex['year']})")
                print(f"      Entry: {ex['ep']:.2f} | SL: {ex['sl']:.2f} (Risk: {ex['risk_pct']:.2f}%) | TP: {ex['tp']:.2f} (Reward: {ex['reward_pct']:.2f}%, {ex['prov']})")
                print(f"      Planned RR: {ex['rr']:.2f}R | Span Progress: {ex['span_progress']:.1f}% | Latency: {ex['latency_hours']:.1f}h")

if __name__ == "__main__":
    run_decomposition()
