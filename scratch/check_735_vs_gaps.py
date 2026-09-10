import json
from datetime import datetime, timezone

with open("scratch/canonical_735_opportunity_ledger.json") as f:
    opportunities = json.load(f)

print(f"Total LTF-confirmed opportunities: {len(opportunities)}")

with open("scratch/data_gap_inventory.json") as f:
    all_gaps = json.load(f)

in_dev_gaps = [g for g in all_gaps if g["is_in_dev_partition"]]

# Unique gap intervals
gap_intervals = []
seen = set()
for g in in_dev_gaps:
    k = (g["symbol"], g["prev_timestamp"], g["curr_timestamp"])
    if k not in seen:
        seen.add(k)
        gap_intervals.append({
            "symbol": g["symbol"],
            "start": g["prev_timestamp"],
            "end": g["curr_timestamp"],
            "start_utc": g["prev_utc"],
            "end_utc": g["curr_utc"],
            "tf": g["timeframe"],
            "missing": g["missing_bars"]
        })

direct_overlap_candidates = []
proximity_12h_candidates = []

for opp in opportunities:
    sym = opp.get("symbol")
    ts = opp.get("timestamp")
    if not ts or not sym:
        continue
    
    for gi in gap_intervals:
        if gi["symbol"] == sym:
            # Check if trigger falls inside gap
            if ts >= gi["start"] and ts <= gi["end"]:
                direct_overlap_candidates.append((opp, gi))
            # Check if within 12 hours of gap
            elif abs(ts - gi["start"]) <= 12 * 3600 or abs(ts - gi["end"]) <= 12 * 3600:
                proximity_12h_candidates.append((opp, gi))

print(f"Opportunities directly inside a data gap: {len(direct_overlap_candidates)}")
print(f"Opportunities within +/- 12 hours of a data gap: {len(proximity_12h_candidates)}")

if direct_overlap_candidates:
    print("\nDirect overlap details:")
    for opp, gi in direct_overlap_candidates:
        print(f"  {opp['candidate_id']} at {opp['entry_timestamp']} inside {gi['symbol']} {gi['tf']} {gi['start_utc']} -> {gi['end_utc']}")

if proximity_12h_candidates:
    print("\nProximity details:")
    for opp, gi in proximity_12h_candidates[:10]:
        print(f"  {opp['candidate_id']} near {gi['symbol']} {gi['tf']} {gi['start_utc']} -> {gi['end_utc']}")
