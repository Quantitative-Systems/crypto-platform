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
print(f"Total LTF-confirmed candidates: {len(ltf_confirmed)}")

TF_MAP = {"SET_1": "1d", "SET_2": "4h", "SET_3": "1h", "SET_4": "15m"}
LIFESPAN_SEC = {"SET_1": 21 * 86400, "SET_2": 7 * 86400, "SET_3": 48 * 3600, "SET_4": 12 * 3600}

# Load candles
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

# Load Composite trade IDs
with open('scratch/composite_01_dev_results.json') as f:
    comp_data = json.load(f)
composite_trade_ids = set(t['trade_id'] for t in comp_data.get('all_trades', []))
a2_trade_ids = set(t['trade_id'] for t in data.get('all_trades', []))

# Build exhaustive ledger for all 735 opportunities
ledger_735 = []

for c in ltf_confirmed:
    cand_id = c.get("candidate_id")
    stream_id = c.get("stream_id")
    symbol = f"{c['asset']}/USDT"
    tf_set = c.get("tf_set")
    ltf_tf = TF_MAP.get(tf_set)
    dir_perm = c.get("directional_permission")
    is_long = ("LONG" in str(dir_perm))
    ts = c.get("ltf_confirmation_timestamp")
    entry_p = c.get("ltf_entry_price")
    sl_p = c.get("ltf_structural_sl")
    tp_p = c.get("htf_target_price")
    
    stop_dist = abs(entry_p - sl_p) if (entry_p and sl_p) else 0.0
    target_dist = abs(tp_p - entry_p) if (entry_p and tp_p) else 0.0
    planned_rr = (target_dist / stop_dist) if (stop_dist > 0 and target_dist > 0) else 0.0
    
    state = c.get("state")
    inv_reason = c.get("invalidation_reason") or ("TARGET_RESOLVED" if state == "ENTERED" else "UNKNOWN")

    # Polarity check
    cdl = candles_dict_cache.get((symbol, ltf_tf), {}).get(ts)
    polarity_pass = False
    if cdl:
        polarity_pass = (cdl.close > cdl.open) if is_long else (cdl.close < cdl.open)

    # Reconcile with A2 Executed Trades (23) and Composite Trades (13)
    is_a2_executed = (cand_id in a2_trade_ids)
    is_composite_executed = (cand_id in composite_trade_ids)

    # Counterfactual excursion (until initial stop-out)
    cdls = candles_list_cache.get((symbol, ltf_tf), [])
    trig_idx = -1
    for idx, cd in enumerate(cdls):
        if cd.timestamp == ts:
            trig_idx = idx
            break

    mfe_r = 0.0
    mae_r = 0.0
    time_to_mfe = 0
    time_to_mae = 0
    excursion_exit_reason = "NO_DATA"

    if trig_idx != -1 and stop_dist > 0:
        peak_fav = entry_p
        peak_adv = entry_p
        for step, cd in enumerate(cdls[trig_idx + 1:], 1):
            if is_long:
                hit_sl = (cd.low <= sl_p)
                hit_tp = (cd.high >= tp_p) if tp_p else False
                if cd.low < peak_adv:
                    peak_adv = cd.low
                    time_to_mae = cd.timestamp - ts
                if hit_sl:
                    peak_adv = min(peak_adv, sl_p)
                    excursion_exit_reason = "STOP_OUT"
                    break
                if cd.high > peak_fav:
                    peak_fav = cd.high
                    time_to_mfe = cd.timestamp - ts
                if hit_tp:
                    excursion_exit_reason = "TARGET_HIT"
                    break
            else:
                hit_sl = (cd.high >= sl_p)
                hit_tp = (cd.low <= tp_p) if tp_p else False
                if cd.high > peak_adv:
                    peak_adv = cd.high
                    time_to_mae = cd.timestamp - ts
                if hit_sl:
                    peak_adv = max(peak_adv, sl_p)
                    excursion_exit_reason = "STOP_OUT"
                    break
                if cd.low < peak_fav:
                    peak_fav = cd.low
                    time_to_mfe = cd.timestamp - ts
                if hit_tp:
                    excursion_exit_reason = "TARGET_HIT"
                    break
        mfe_r = (peak_fav - entry_p) / stop_dist if is_long else (entry_p - peak_fav) / stop_dist
        mae_r = (entry_p - peak_adv) / stop_dist if is_long else (peak_adv - entry_p) / stop_dist

    # Lifecycle stage & disposition categorization
    # Categories:
    # 1. RR < 4R Rejection: REJECT_RR_BELOW_4R
    # 2. Target Geometry Rejection: REJECT_INVALID_ANCHOR_GEOMETRY
    # 3. Missing/Invalid Anchor Rejection: REJECT_MISSING_STRUCTURAL_ANCHORS
    # 4. Opposing MTF Structure Invalidation: REJECT_OPPOSING_MTF_STRUCTURE
    # 5. Superseded HTF Context Invalidation: REJECT_SUPERSEDED_HTF_CONTEXT
    # 6. Target Resolved - Pending Unfilled (passed 4R, but limit entry never hit)
    # 7. Target Resolved - Filled - Polarity Filtered (A2 trade 10 trades)
    # 8. Target Resolved - Filled - Composite Executed (13 trades)
    if inv_reason == "REJECT_RR_BELOW_4R":
        lifecycle_category = "RR_LT_4R_REJECTION"
    elif inv_reason == "REJECT_INVALID_ANCHOR_GEOMETRY":
        lifecycle_category = "TARGET_GEOMETRY_REJECTION"
    elif inv_reason == "REJECT_MISSING_STRUCTURAL_ANCHORS":
        lifecycle_category = "MISSING_ANCHOR_REJECTION"
    elif inv_reason == "REJECT_OPPOSING_MTF_STRUCTURE":
        lifecycle_category = "SUPERSEDED_OPPOSING_MTF_STRUCTURE"
    elif inv_reason == "REJECT_SUPERSEDED_HTF_CONTEXT":
        lifecycle_category = "SUPERSEDED_HTF_CONTEXT"
    elif state == "ENTERED":
        if is_composite_executed:
            lifecycle_category = "COMPOSITE_EXECUTED"
        elif is_a2_executed:
            lifecycle_category = "POLARITY_FILTERED_A2_TRADE"
        else:
            lifecycle_category = "PENDING_LIMIT_UNFILLED"
    else:
        lifecycle_category = f"OTHER_{inv_reason}"

    record = {
        "candidate_id": cand_id,
        "stream_id": stream_id,
        "symbol": symbol,
        "timeframe_set": tf_set,
        "direction": "LONG" if is_long else "SHORT",
        "timestamp": ts,
        "datetime_utc": datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        "entry_price": entry_p,
        "initial_sl": sl_p,
        "target_price": tp_p,
        "planned_rr": round(planned_rr, 4),
        "lifecycle_stage": state,
        "final_disposition": lifecycle_category,
        "rejection_reason": inv_reason,
        "passed_target_resolution": (state == "ENTERED"),
        "polarity_eligible": polarity_pass,
        "a2_executed": is_a2_executed,
        "composite_executed": is_composite_executed,
        "counterfactual_mfe_r": round(mfe_r, 4),
        "counterfactual_mae_r": round(mae_r, 4),
        "time_to_mfe_hours": round(time_to_mfe / 3600.0, 2),
        "time_to_mae_hours": round(time_to_mae / 3600.0, 2),
        "excursion_exit_reason": excursion_exit_reason,
        "reach_1r": mfe_r >= 1.0,
        "reach_2r": mfe_r >= 2.0,
        "reach_2_5r": mfe_r >= 2.5,
        "reach_3r": mfe_r >= 3.0,
        "reach_4r": mfe_r >= 4.0,
    }
    ledger_735.append(record)

# Save ledger
with open('scratch/canonical_735_opportunity_ledger.json', 'w') as f:
    json.dump(ledger_735, f, indent=2)

print("Saved scratch/canonical_735_opportunity_ledger.json")

# Category summary
from collections import Counter
cat_counts = Counter(r["final_disposition"] for r in ledger_735)
print("\nFinal Disposition Breakdown across 735 LTF Confirmations:")
total = len(ledger_735)
for cat, cnt in cat_counts.most_common():
    print(f"  {cat:35s}: {cnt:4d} ({cnt/total*100:5.2f}%)")
print(f"  Total: {sum(cat_counts.values())}")
