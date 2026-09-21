import json
import numpy as np
from datetime import datetime, timezone
import os
import sys

sys.path.insert(0, '/home/mrcn2/crypto-platform')
from market_data.warehouse_loader import WarehouseLoader

with open('scratch/anchor2_dev_certified_results.json') as f:
    data = json.load(f)

streams = data.get("stream_results", [])
all_cands = []
for s in streams:
    for c in s.get("all_candidates", []):
        c["stream_id"] = s.get("stream_id")
        c["tf_set"] = s.get("timeframe_set")
        c["asset"] = s.get("asset")
        all_cands.append(c)

ltf_confirmed = [c for c in all_cands if "RISK_GATE" in c.get("stages_reached", [])]
rr_rejected = [c for c in ltf_confirmed if c.get("invalidation_reason") == "REJECT_RR_BELOW_4R"]

TF_MAP = {"SET_1": "1d", "SET_2": "4h", "SET_3": "1h", "SET_4": "15m"}
LIFESPAN_SEC = {"SET_1": 21 * 86400, "SET_2": 7 * 86400, "SET_3": 48 * 3600, "SET_4": 12 * 3600}

candles_list_cache = {}
candles_dict_cache = {}
for asset in ["BTC", "ETH", "SOL"]:
    symbol = f"{asset}/USDT"
    for set_id, ltf_tf in TF_MAP.items():
        key = (symbol, ltf_tf)
        if key not in candles_list_cache:
            ltf_start = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
            ltf_end = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
            cdls = WarehouseLoader.load_history(symbol, ltf_tf, limit=1_000_000, start_time_ms=ltf_start, end_time_ms=ltf_end)
            cdls.sort(key=lambda x: x.timestamp)
            candles_list_cache[key] = cdls
            candles_dict_cache[key] = {c.timestamp: c for c in cdls}

# Label displacement polarity for each
for c in rr_rejected:
    sym = f"{c['asset']}/USDT"
    ltf_tf = TF_MAP.get(c.get("tf_set"))
    ts = c.get("ltf_confirmation_timestamp")
    cdl = candles_dict_cache.get((sym, ltf_tf), {}).get(ts)
    is_long = ("LONG" in str(c.get("directional_permission")))
    if cdl:
        if is_long:
            c["polarity_eligible"] = (cdl.close > cdl.open)
        else:
            c["polarity_eligible"] = (cdl.close < cdl.open)
    else:
        c["polarity_eligible"] = False

def run_excursion_sim(cands, horizon_type="STOP_OUT"):
    results = []
    for cand in cands:
        sym = f"{cand['asset']}/USDT"
        tf_set = cand.get("tf_set")
        ltf_tf = TF_MAP.get(tf_set)
        ts = cand.get("ltf_confirmation_timestamp")
        entry = cand.get("ltf_entry_price")
        sl = cand.get("ltf_structural_sl")
        tp = cand.get("htf_target_price")
        is_long = ("LONG" in str(cand.get("directional_permission")))
        risk_dist = abs(entry - sl)
        if risk_dist <= 0:
            continue

        cdls = candles_list_cache.get((sym, ltf_tf), [])
        trig_idx = -1
        for idx, c in enumerate(cdls):
            if c.timestamp == ts:
                trig_idx = idx
                break
        if trig_idx == -1:
            continue

        max_sec = None
        if horizon_type == "LIFESPAN":
            max_sec = LIFESPAN_SEC.get(tf_set, 48 * 3600)
        elif horizon_type == "BARS_48":
            dur = cdls[1].timestamp - cdls[0].timestamp if len(cdls) > 1 else 900
            max_sec = dur * 48

        peak_fav = entry
        peak_adv = entry
        time_to_mfe = 0
        time_to_mae = 0
        exit_reason = "END_OF_WINDOW"
        exit_step = 0

        for step, c in enumerate(cdls[trig_idx + 1:], 1):
            if max_sec and (c.timestamp - ts) > max_sec:
                exit_reason = "TIMEOUT"
                exit_step = step
                break

            if is_long:
                hit_sl = (c.low <= sl)
                hit_tp = (c.high >= tp) if tp else False
                if c.low < peak_adv:
                    peak_adv = c.low
                    time_to_mae = c.timestamp - ts
                if hit_sl:
                    peak_adv = min(peak_adv, sl)
                    exit_reason = "STOP_OUT"
                    exit_step = step
                    break
                if c.high > peak_fav:
                    peak_fav = c.high
                    time_to_mfe = c.timestamp - ts
                if hit_tp:
                    exit_reason = "TARGET_HIT"
                    exit_step = step
                    break
            else:
                hit_sl = (c.high >= sl)
                hit_tp = (c.low <= tp) if tp else False
                if c.high > peak_adv:
                    peak_adv = c.high
                    time_to_mae = c.timestamp - ts
                if hit_sl:
                    peak_adv = max(peak_adv, sl)
                    exit_reason = "STOP_OUT"
                    exit_step = step
                    break
                if c.low < peak_fav:
                    peak_fav = c.low
                    time_to_mfe = c.timestamp - ts
                if hit_tp:
                    exit_reason = "TARGET_HIT"
                    exit_step = step
                    break

        mfe_r = (peak_fav - entry) / risk_dist if is_long else (entry - peak_fav) / risk_dist
        mae_r = (entry - peak_adv) / risk_dist if is_long else (peak_adv - entry) / risk_dist

        results.append({
            "cand": cand,
            "mfe_r": mfe_r,
            "mae_r": mae_r,
            "time_to_mfe": time_to_mfe,
            "time_to_mae": time_to_mae,
            "exit_reason": exit_reason,
            "exit_step": exit_step
        })
    return results

def print_stats(title, res_list):
    n = len(res_list)
    if n == 0:
        print(f"{title}: N=0")
        return
    mfes = np.array([r["mfe_r"] for r in res_list])
    maes = np.array([r["mae_r"] for r in res_list])
    t_mfes = np.array([r["time_to_mfe"] for r in res_list])
    t_maes = np.array([r["time_to_mae"] for r in res_list])

    r_1r = sum(mfes >= 1.0)
    r_2r = sum(mfes >= 2.0)
    r_2_5r = sum(mfes >= 2.5)
    r_3r = sum(mfes >= 3.0)
    r_4r = sum(mfes >= 4.0)

    print(f"\n=======================================================")
    print(f"{title} (N = {n})")
    print(f"=======================================================")
    print(f"MFE: Mean={np.mean(mfes):.4f}R, Median={np.median(mfes):.4f}R, Std={np.std(mfes):.4f}R, Min={np.min(mfes):.4f}R, Max={np.max(mfes):.4f}R")
    print(f"     Q1={np.percentile(mfes, 25):.4f}R, Q3={np.percentile(mfes, 75):.4f}R")
    print(f"MAE: Mean={np.mean(maes):.4f}R, Median={np.median(maes):.4f}R, Std={np.std(maes):.4f}R, Max={np.max(maes):.4f}R")
    print(f"Time to MFE (hours): Mean={np.mean(t_mfes)/3600:.2f}h, Median={np.median(t_mfes)/3600:.2f}h")
    print(f"Time to MAE (hours): Mean={np.mean(t_maes)/3600:.2f}h, Median={np.median(t_maes)/3600:.2f}h")
    print(f"Reach >= 1.0R: {r_1r:4d} ({r_1r/n*100:5.2f}%)")
    print(f"Reach >= 2.0R: {r_2r:4d} ({r_2r/n*100:5.2f}%)")
    print(f"Reach >= 2.5R: {r_2_5r:4d} ({r_2_5r/n*100:5.2f}%)")
    print(f"Reach >= 3.0R: {r_3r:4d} ({r_3r/n*100:5.2f}%)")
    print(f"Reach >= 4.0R: {r_4r:4d} ({r_4r/n*100:5.2f}%)")
    print("MFE Buckets:")
    print(f"  < 1.0R:     {sum(mfes < 1.0):4d} ({sum(mfes < 1.0)/n*100:5.2f}%)")
    print(f"  1.0 - 2.0R: {sum((mfes >= 1.0) & (mfes < 2.0)):4d} ({sum((mfes >= 1.0) & (mfes < 2.0))/n*100:5.2f}%)")
    print(f"  2.0 - 2.5R: {sum((mfes >= 2.0) & (mfes < 2.5)):4d} ({sum((mfes >= 2.0) & (mfes < 2.5))/n*100:5.2f}%)")
    print(f"  2.5 - 3.0R: {sum((mfes >= 2.5) & (mfes < 3.0)):4d} ({sum((mfes >= 2.5) & (mfes < 3.0))/n*100:5.2f}%)")
    print(f"  3.0 - 4.0R: {sum((mfes >= 3.0) & (mfes < 4.0)):4d} ({sum((mfes >= 3.0) & (mfes < 4.0))/n*100:5.2f}%)")
    print(f"  >= 4.0R:    {sum(mfes >= 4.0):4d} ({sum(mfes >= 4.0)/n*100:5.2f}%)")

# Run simulations
# Horizon 1: Stop-out horizon (natural causal trade life)
res_all_stop = run_excursion_sim(rr_rejected, "STOP_OUT")
res_pol_elig_stop = [r for r in res_all_stop if r["cand"]["polarity_eligible"]]
res_pol_filt_stop = [r for r in res_all_stop if not r["cand"]["polarity_eligible"]]

print_stats("ALL 4R-REJECTED (HORIZON: UNTIL STOP-OUT)", res_all_stop)
print_stats("4R-REJECTED + POLARITY-ELIGIBLE (HORIZON: UNTIL STOP-OUT)", res_pol_elig_stop)
print_stats("4R-REJECTED + POLARITY-FILTERED (HORIZON: UNTIL STOP-OUT)", res_pol_filt_stop)

# Horizon 2: Candidate Lifespan TTL horizon (sensitivity)
res_all_life = run_excursion_sim(rr_rejected, "LIFESPAN")
res_pol_elig_life = [r for r in res_all_life if r["cand"]["polarity_eligible"]]
res_pol_filt_life = [r for r in res_all_life if not r["cand"]["polarity_eligible"]]

print_stats("ALL 4R-REJECTED (HORIZON: CANDIDATE TTL LIFESPAN)", res_all_life)
print_stats("4R-REJECTED + POLARITY-ELIGIBLE (HORIZON: CANDIDATE TTL LIFESPAN)", res_pol_elig_life)
print_stats("4R-REJECTED + POLARITY-FILTERED (HORIZON: CANDIDATE TTL LIFESPAN)", res_pol_filt_life)
