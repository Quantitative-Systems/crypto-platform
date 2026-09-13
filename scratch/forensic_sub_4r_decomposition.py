import sys
sys.path.insert(0, "/home/mrcn2/crypto-platform")
import json
from collections import defaultdict
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

def run_decomposition():
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

    print(f"Total setups rejected by >=4R firewall: {len(rejected_4r)}")

    # 1. Distribution by Asset & Timeframe Set
    by_asset = defaultdict(list)
    by_tf = defaultdict(list)
    for c in rejected_4r:
        by_asset[c["asset"]].append(c)
        by_tf[c["timeframe_set"]].append(c)

    print("\n=== DISTRIBUTION BY ASSET ===")
    for a, cands in sorted(by_asset.items()):
        print(f"  {a:6s}: {len(cands):3d} setups ({len(cands)/len(rejected_4r)*100:.1f}%)")

    print("\n=== DISTRIBUTION BY TIMEFRAME SET ===")
    for tf, cands in sorted(by_tf.items()):
        print(f"  {tf:6s}: {len(cands):3d} setups ({len(cands)/len(rejected_4r)*100:.1f}%)")

    # 2. Planned RR Breakdown
    rr_brackets = {
        ">= 3.0R": [],
        "2.5R - 3.0R": [],
        "2.0R - 2.5R": [],
        "1.5R - 2.0R": [],
        "1.0R - 1.5R": [],
        "< 1.0R": []
    }

    classified_setups = []
    for c in rejected_4r:
        ep = c.get("ltf_entry_price")
        sl = c.get("ltf_structural_sl")
        tp = c.get("htf_target_price")
        is_long = "BULLISH" in str(c.get("htf_macro_direction", "")) or "LONG" in str(c.get("candidate_id", ""))
        # Verify direction from SL vs Entry
        if sl is not None and ep is not None:
            is_long = (sl < ep)
        
        stop_dist = abs(ep - sl) if (ep and sl) else 0.0
        target_dist = abs(tp - ep) if (tp and ep) else 0.0
        raw_rr = target_dist / stop_dist if stop_dist > 0 else 0.0
        stop_pct = (stop_dist / ep) * 100.0 if ep else 0.0
        target_pct = (target_dist / ep) * 100.0 if ep else 0.0

        c["is_long"] = is_long
        c["raw_rr"] = raw_rr
        c["stop_pct"] = stop_pct
        c["target_pct"] = target_pct
        c["stop_dist"] = stop_dist
        c["target_dist"] = target_dist

        if raw_rr >= 3.0:
            rr_brackets[">= 3.0R"].append(c)
        elif raw_rr >= 2.5:
            rr_brackets["2.5R - 3.0R"].append(c)
        elif raw_rr >= 2.0:
            rr_brackets["2.0R - 2.5R"].append(c)
        elif raw_rr >= 1.5:
            rr_brackets["1.5R - 2.0R"].append(c)
        elif raw_rr >= 1.0:
            rr_brackets["1.0R - 1.5R"].append(c)
        else:
            rr_brackets["< 1.0R"].append(c)

        # Classification into Categories:
        # A: genuine lower-RR (RR >= 2.0R, clean structure)
        # B: structurally weak (large latency or opposing structure)
        # C: poor stop geometry (stop_pct > 3.0% or oversized stop)
        # D: target too close / market compression (target_pct < 1.0% or raw_rr < 1.0R)
        # E: requires different management model
        if raw_rr >= 2.0:
            category = "A_GENUINE_LOWER_RR"
        elif stop_pct > 3.5:
            category = "C_POOR_STOP_GEOMETRY"
        elif target_pct < 1.5 or raw_rr < 1.0:
            category = "D_MARKET_COMPRESSION"
        elif "PULLBACK" in str(c.get("htf_context", "")):
            category = "E_MANAGEMENT_SENSITIVE"
        else:
            category = "B_STRUCTURALLY_WEAK"

        c["category"] = category
        classified_setups.append(c)

    print("\n=== PLANNED RR BRACKET COUNTS ===")
    for b, cands in rr_brackets.items():
        print(f"  {b:12s}: {len(cands):3d} setups ({len(cands)/len(rejected_4r)*100:.1f}%)")

    cat_counts = defaultdict(int)
    for c in classified_setups:
        cat_counts[c["category"]] += 1

    print("\n=== CLASSIFICATION TAXONOMY (A through E) ===")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat:25s}: {count:3d} setups ({count/len(rejected_4r)*100:.1f}%)")

    # 3. Simulate forward for candidates with RR >= 2.0R to evaluate Counterfactual Performance!
    print("\n=== FORWARD SIMULATION OF SUB-4R CANDIDATES (RR >= 2.0R) ===")
    print(f"{'#':2s} | {'Candidate ID':36s} | {'Asset':5s} | {'Set':5s} | {'Dir':5s} | {'Planned RR':10s} | {'MFE (R)':8s} | {'MAE (R)':8s} | {'Outcome':15s}")
    print("-" * 110)

    # Cache candle loader
    candle_cache = {}
    eligible_cands = [c for c in classified_setups if c["raw_rr"] >= 2.0]
    eligible_cands.sort(key=lambda x: x.get("ltf_confirmation_timestamp", 0))

    sim_results = []
    for idx, c in enumerate(eligible_cands):
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
        risk_dist = abs(ep - sl)
        target_dist = abs(tp - ep)

        # Find entry candle index
        e_idx = None
        for i, candle in enumerate(candles):
            if candle.timestamp == entry_ts:
                e_idx = i
                break
        
        if e_idx is None or e_idx >= len(candles) - 1:
            print(f"{idx+1:02d} | {c['candidate_id']:36s} | {c['asset']:5s} | {tf_set_id:5s} | NO_CANDLE_DATA")
            continue

        # Forward simulate from e_idx + 1
        max_fav = ep
        max_adv = ep
        hit_tp = False
        hit_sl = False
        exit_ts = None
        exit_reason = "TIMEOUT"
        exit_price = ep
        current_sl = sl

        for bar in candles[e_idx + 1:]:
            # Adverse-first collision check
            if is_long:
                fav = bar.high
                adv = bar.low
                if fav > max_fav:
                    max_fav = fav
                if adv < max_adv:
                    max_adv = adv

                # Check SL hit
                if adv <= current_sl:
                    hit_sl = True
                    exit_reason = "SL_HIT"
                    exit_price = current_sl
                    exit_ts = bar.timestamp
                    break
                # Check TP hit
                if fav >= tp:
                    hit_tp = True
                    exit_reason = "TP_HIT"
                    exit_price = tp
                    exit_ts = bar.timestamp
                    break
            else:
                fav = bar.low
                adv = bar.high
                if fav < max_fav:
                    max_fav = fav
                if adv > max_adv:
                    max_adv = adv

                if adv >= current_sl:
                    hit_sl = True
                    exit_reason = "SL_HIT"
                    exit_price = current_sl
                    exit_ts = bar.timestamp
                    break
                if fav <= tp:
                    hit_tp = True
                    exit_reason = "TP_HIT"
                    exit_price = tp
                    exit_ts = bar.timestamp
                    break

        mfe_r = abs(max_fav - ep) / risk_dist if risk_dist > 0 else 0.0
        mae_r = abs(max_adv - ep) / risk_dist if risk_dist > 0 else 0.0

        if hit_tp:
            realized_r = c["raw_rr"] - 0.02 # friction approx
            outcome = f"WIN (+{realized_r:.2f}R)"
        elif hit_sl:
            realized_r = -1.05 # friction approx
            outcome = f"LOSS (-1.05R)"
        else:
            realized_r = 0.0
            outcome = "OPEN/TIMEOUT"

        sim_results.append({
            "candidate_id": c["candidate_id"],
            "asset": c["asset"],
            "timeframe_set": tf_set_id,
            "direction": "LONG" if is_long else "SHORT",
            "entry_ts": entry_ts,
            "entry_price": ep,
            "stop_price": sl,
            "target_price": tp,
            "planned_rr": c["raw_rr"],
            "mfe_r": mfe_r,
            "mae_r": mae_r,
            "exit_reason": exit_reason,
            "realized_r": realized_r,
            "outcome": outcome
        })

        print(f"{idx+1:02d} | {c['candidate_id']:36s} | {c['asset']:5s} | {tf_set_id:5s} | {'LONG' if is_long else 'SHORT':5s} | {c['raw_rr']:8.2f}R | {mfe_r:7.2f}R | {mae_r:7.2f}R | {outcome:15s}")

    # Summary by RR threshold
    print("\n=== SUMMARY OF LOWER RR COUNTERFACTUAL ECONOMICS ===")
    for thresh in [3.0, 2.5, 2.0]:
        subset = [s for s in sim_results if s["planned_rr"] >= thresh]
        n = len(subset)
        wins = sum(1 for s in subset if s["realized_r"] > 0)
        losses = sum(1 for s in subset if s["realized_r"] < 0)
        net_r = sum(s["realized_r"] for s in subset)
        gross_win = sum(s["realized_r"] for s in subset if s["realized_r"] > 0)
        gross_loss = abs(sum(s["realized_r"] for s in subset if s["realized_r"] < 0))
        pf = gross_win / gross_loss if gross_loss > 0 else 999.0
        exp = net_r / n if n > 0 else 0.0
        wr = wins / n * 100 if n > 0 else 0.0
        print(f"Threshold >= {thresh:.1f}R: N={n:2d} | Wins={wins:2d} | Losses={losses:2d} | WR={wr:5.1f}% | Net R={net_r:+6.2f}R | PF={pf:5.2f} | Exp={exp:+5.2f}R")

if __name__ == "__main__":
    run_decomposition()
