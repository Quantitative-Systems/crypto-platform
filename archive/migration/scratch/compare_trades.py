import json
import os

with open("scratch/canonical_h0_dev_results.json") as f:
    baseline = json.load(f)

print("Baseline Trades (total 8):")
for stream in baseline.get("stream_results", []):
    for trade in stream.get("trades", []):
        print(f"  {stream['stream_id']} - Entry: {trade['entry_timestamp']} at {trade['entry_price']} | SL: {trade['sl_price']} | TP: {trade['tp_price']}")
        
# I need to modify run_canonical_v21_diagnostic.py to dump the results to compare!
