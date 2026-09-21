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

print(f"Total LTF-confirmed: {len(ltf_confirmed)}")
print(f"Total RR < 4R rejected: {len(rr_rejected)}")

# Load LTF candle caches for BTC, ETH, SOL across SET_1..4
# SET_1: ltf is 1d
# SET_2: ltf is 4h
# SET_3: ltf is 1h
# SET_4: ltf is 15m

TF_MAP = {
    "SET_1": "1d",
    "SET_2": "4h",
    "SET_3": "1h",
    "SET_4": "15m",
}

candles_cache = {}
for asset in ["BTC", "ETH", "SOL"]:
    symbol = f"{asset}/USDT"
    for set_id, ltf_tf in TF_MAP.items():
        key = (symbol, ltf_tf)
        if key not in candles_cache:
            try:
                # 2021-2022
                ltf_start = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
                ltf_end = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
                cdls = WarehouseLoader.load_history(symbol, ltf_tf, limit=1_000_000, start_time_ms=ltf_start, end_time_ms=ltf_end)
                candles_cache[key] = {c.timestamp: c for c in cdls}
            except Exception as e:
                print(f"Error loading {key}: {e}")

# Evaluate displacement polarity on the 671 RR-rejected
polarity_eligible_rr = []
polarity_filtered_rr = []
polarity_unmatched_rr = []

for c in rr_rejected:
    sym = f"{c['asset']}/USDT"
    tf_set = c.get("tf_set")
    ltf_tf = TF_MAP.get(tf_set)
    ts = c.get("ltf_confirmation_timestamp")
    dir_perm = c.get("directional_permission")
    is_long = ("LONG" in str(dir_perm))

    cdl_dict = candles_cache.get((sym, ltf_tf), {})
    cdl = cdl_dict.get(ts)
    if not cdl:
        # try matching closest or exact
        polarity_unmatched_rr.append(c)
        continue

    # Polarity logic:
    # Long: requires close > open
    # Short: requires close < open
    if is_long:
        if cdl.close > cdl.open:
            polarity_eligible_rr.append((c, cdl))
        else:
            polarity_filtered_rr.append((c, cdl))
    else:
        if cdl.close < cdl.open:
            polarity_eligible_rr.append((c, cdl))
        else:
            polarity_filtered_rr.append((c, cdl))

print(f"\nDisplacement Polarity on the 671 RR < 4R Rejected Population:")
print(f"  Matched candles: {len(polarity_eligible_rr) + len(polarity_filtered_rr)} / {len(rr_rejected)}")
print(f"  Unmatched candles: {len(polarity_unmatched_rr)}")
print(f"  Polarity-Eligible (conforming trigger): {len(polarity_eligible_rr)} ({len(polarity_eligible_rr)/len(rr_rejected)*100:.2f}%)")
print(f"  Polarity-Filtered (non-conforming trigger): {len(polarity_filtered_rr)} ({len(polarity_filtered_rr)/len(rr_rejected)*100:.2f}%)")

# Planned RR among Polarity-Eligible
rrs_eligible = []
for c, cdl in polarity_eligible_rr:
    entry = c.get("ltf_entry_price")
    sl = c.get("ltf_structural_sl")
    tp = c.get("htf_target_price")
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    rrs_eligible.append(rr)

rrs_eligible = np.array(rrs_eligible)
print("\nPlanned RR Distribution among Polarity-Eligible 4R-rejected:")
print(f"  Count: {len(rrs_eligible)}")
print(f"  Min: {np.min(rrs_eligible):.4f}R")
print(f"  Median: {np.median(rrs_eligible):.4f}R")
print(f"  Mean: {np.mean(rrs_eligible):.4f}R")
print(f"  Max: {np.max(rrs_eligible):.4f}R")
print(f"  < 1.0R:     {sum(rrs_eligible < 1.0)} ({sum(rrs_eligible < 1.0)/len(rrs_eligible)*100:.2f}%)")
print(f"  1.0 - 2.0R: {sum((rrs_eligible >= 1.0) & (rrs_eligible < 2.0))} ({sum((rrs_eligible >= 1.0) & (rrs_eligible < 2.0))/len(rrs_eligible)*100:.2f}%)")
print(f"  2.0 - 2.5R: {sum((rrs_eligible >= 2.0) & (rrs_eligible < 2.5))} ({sum((rrs_eligible >= 2.0) & (rrs_eligible < 2.5))/len(rrs_eligible)*100:.2f}%)")
print(f"  >= 2.5R:    {sum(rrs_eligible >= 2.5)} ({sum(rrs_eligible >= 2.5)/len(rrs_eligible)*100:.2f}%)")
