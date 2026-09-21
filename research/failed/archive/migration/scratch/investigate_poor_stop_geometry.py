import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
import json
import numpy as np
from collections import defaultdict
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

def investigate_poor_stop_geometry():
    with open("scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json", "r") as f:
        d = json.load(f)

    rejected_4r = []
    for s in d.get("stream_results", []):
        s_id = s.get("stream_id")
        asset = s.get("asset")
        tf_set = s.get("timeframe_set")
        for c in s.get("all_candidates", []):
            if c.get("invalidation_reason") == "REJECT_RR_BELOW_4R":
                c_copy = dict(c)
                c_copy["stream_id"] = s_id
                c_copy["asset"] = asset
                c_copy["symbol"] = s.get("symbol") or f"{asset}/USDT"
                c_copy["timeframe_set"] = tf_set
                rejected_4r.append(c_copy)

    # Classify Category C: Poor Stop Geometry (stop_pct > 3.5%)
    cat_c = []
    for c in rejected_4r:
        ep = c.get("ltf_entry_price")
        sl = c.get("ltf_structural_sl")
        tp = c.get("htf_target_price")
        if ep is None or sl is None or tp is None:
            continue
        is_long = (sl < ep)
        stop_dist = abs(ep - sl)
        target_dist = abs(tp - ep)
        stop_pct = (stop_dist / ep) * 100.0
        target_pct = (target_dist / ep) * 100.0
        raw_rr = target_dist / stop_dist if stop_dist > 0 else 0.0

        c["is_long"] = is_long
        c["stop_dist"] = stop_dist
        c["target_dist"] = target_dist
        c["stop_pct"] = stop_pct
        c["target_pct"] = target_pct
        c["raw_rr"] = raw_rr

        # Category C: stop_pct > 3.5%
        if raw_rr < 2.0 and stop_pct > 3.5:
            cat_c.append(c)

    print(f"Total Category C (Stop > 3.5%): {len(cat_c)} out of {len(rejected_4r)} rejected setups ({len(cat_c)/len(rejected_4r)*100:.1f}%)")

    # Stop distribution
    stop_pcts = [c["stop_pct"] for c in cat_c]
    target_pcts = [c["target_pct"] for c in cat_c]
    raw_rrs = [c["raw_rr"] for c in cat_c]

    print(f"Stop %: Mean={np.mean(stop_pcts):.2f}%, Median={np.median(stop_pcts):.2f}%, Min={np.min(stop_pcts):.2f}%, Max={np.max(stop_pcts):.2f}%")
    print(f"Target %: Mean={np.mean(target_pcts):.2f}%, Median={np.median(target_pcts):.2f}%, Min={np.min(target_pcts):.2f}%, Max={np.max(target_pcts):.2f}%")
    print(f"Planned RR: Mean={np.mean(raw_rrs):.2f}R, Median={np.median(raw_rrs):.2f}R, Min={np.min(raw_rrs):.2f}R, Max={np.max(raw_rrs):.2f}R")

    # Group by stream
    by_stream = defaultdict(list)
    for c in cat_c:
        by_stream[c["stream_id"]].append(c)
    print("\nStream Breakdown:")
    for s, clist in sorted(by_stream.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {s:12s}: {len(clist):3d} setups")

    # Forward simulate a representative sample or all of Cat C to evaluate MFE / MAE / boundary respect
    candle_cache = {}
    print("\nForward Excursion Simulation for Category C Setups...")
    
    sim_stats = []
    respected_boundary = 0
    hit_target_first = 0
    hit_stop_first = 0
    mfe_r_vals = []
    mae_r_vals = []
    mfe_pct_vals = []

    for c in cat_c:
        sym = c["symbol"]
        tf_set_id = c["timeframe_set"]
        tf_info = TimeframeAligner.get_set(tf_set_id)
        ltf_tf = tf_info.ltf
        cache_key = (sym, ltf_tf)
        if cache_key not in candle_cache:
            candle_cache[cache_key] = WarehouseLoader.load_history(sym, ltf_tf, limit=1_000_000, start_time_ms=1609459200000, end_time_ms=1672531200000)
        
        candles = candle_cache[cache_key]
        entry_ts = c.get("ltf_confirmation_timestamp")
        ep = c["ltf_entry_price"]
        sl = c["ltf_structural_sl"]
        tp = c["htf_target_price"]
        is_long = c["is_long"]
        risk_dist = c["stop_dist"]

        e_idx = None
        for i, candle in enumerate(candles):
            if candle.timestamp == entry_ts:
                e_idx = i
                break
        
        if e_idx is None or e_idx >= len(candles) - 1:
            continue

        max_fav = ep
        max_adv = ep
        hit_tp = False
        hit_sl = False

        # Simulate up to 500 candles forward
        future_candles = candles[e_idx + 1: e_idx + 501]
        for bar in future_candles:
            if is_long:
                if bar.low <= sl:
                    hit_sl = True
                    max_adv = min(max_adv, bar.low)
                    break
                if bar.high >= tp:
                    hit_tp = True
                    max_fav = max(max_fav, bar.high)
                    break
                max_fav = max(max_fav, bar.high)
                max_adv = min(max_adv, bar.low)
            else:
                if bar.high >= sl:
                    hit_sl = True
                    max_adv = max(max_adv, bar.high)
                    break
                if bar.low <= tp:
                    hit_tp = True
                    max_fav = min(max_fav, bar.low)
                    break
                max_fav = min(max_fav, bar.low)
                max_adv = max(max_adv, bar.high)

        fav_dist = abs(max_fav - ep)
        adv_dist = abs(max_adv - ep)
        mfe_r = fav_dist / risk_dist if risk_dist > 0 else 0.0
        mae_r = adv_dist / risk_dist if risk_dist > 0 else 0.0
        mfe_pct = (fav_dist / ep) * 100.0

        mfe_r_vals.append(mfe_r)
        mae_r_vals.append(mae_r)
        mfe_pct_vals.append(mfe_pct)

        if hit_tp:
            hit_target_first += 1
            respected_boundary += 1
        elif hit_sl:
            hit_stop_first += 1
        else:
            if mae_r < 1.0:
                respected_boundary += 1

    total_simmed = len(mfe_r_vals)
    print(f"\nSimulated {total_simmed} setups:")
    print(f"  Hit Target First: {hit_target_first} ({hit_target_first/total_simmed*100:.1f}%)")
    print(f"  Hit Stop First:   {hit_stop_first} ({hit_stop_first/total_simmed*100:.1f}%)")
    print(f"  Respected Stop Boundary (MAE < 1.0R): {respected_boundary} ({respected_boundary/total_simmed*100:.1f}%)")
    print(f"  Average MFE in R: {np.mean(mfe_r_vals):.2f}R (Median: {np.median(mfe_r_vals):.2f}R)")
    print(f"  Average MFE in %: {np.mean(mfe_pct_vals):.2f}% (Median: {np.median(mfe_pct_vals):.2f}%)")
    print(f"  MFE >= 1.0R: {sum(1 for r in mfe_r_vals if r >= 1.0)} ({sum(1 for r in mfe_r_vals if r >= 1.0)/total_simmed*100:.1f}%)")
    print(f"  MFE >= 2.0R: {sum(1 for r in mfe_r_vals if r >= 2.0)} ({sum(1 for r in mfe_r_vals if r >= 2.0)/total_simmed*100:.1f}%)")
    print(f"  MFE >= 3.0R: {sum(1 for r in mfe_r_vals if r >= 3.0)} ({sum(1 for r in mfe_r_vals if r >= 3.0)/total_simmed*100:.1f}%)")

    # Output detailed summary JSON
    results = {
        "category_c_count": len(cat_c),
        "stop_pct": {"mean": np.mean(stop_pcts), "median": np.median(stop_pcts), "min": np.min(stop_pcts), "max": np.max(stop_pcts)},
        "target_pct": {"mean": np.mean(target_pcts), "median": np.median(target_pcts), "min": np.min(target_pcts), "max": np.max(target_pcts)},
        "planned_rr": {"mean": np.mean(raw_rrs), "median": np.median(raw_rrs), "min": np.min(raw_rrs), "max": np.max(raw_rrs)},
        "sim_stats": {
            "total_simmed": total_simmed,
            "hit_target_first": hit_target_first,
            "hit_stop_first": hit_stop_first,
            "hit_target_pct": hit_target_first / total_simmed * 100.0,
            "hit_stop_pct": hit_stop_first / total_simmed * 100.0,
            "respected_boundary_pct": respected_boundary / total_simmed * 100.0,
            "avg_mfe_r": np.mean(mfe_r_vals),
            "median_mfe_r": np.median(mfe_r_vals),
            "avg_mfe_pct": np.mean(mfe_pct_vals),
            "pct_mfe_ge_1r": sum(1 for r in mfe_r_vals if r >= 1.0) / total_simmed * 100.0,
            "pct_mfe_ge_2r": sum(1 for r in mfe_r_vals if r >= 2.0) / total_simmed * 100.0,
        }
    }

    with open("scratch/poor_stop_geometry_investigation.json", "w") as fp:
        json.dump(results, fp, indent=2)
    print("\nSaved report to scratch/poor_stop_geometry_investigation.json")

if __name__ == "__main__":
    investigate_poor_stop_geometry()
