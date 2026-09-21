import json

with open("scratch/exp_d1_dev.json") as f:
    d = json.load(f)

for t in d["all_trades"]:
    prov = t.get("metadata", {}).get("structural_provenance", {})
    if "SWEEP" in prov.get("ltf_entry_reason", ""):
        print("Trade ID:", t["trade_id"], "Symbol:", t["symbol"], "Stream:", t["stream_id"])
        print("  entry_reason:", prov.get("ltf_entry_reason"))
        print("  entry_ts:", t["entry_timestamp"], "retest_ts:", prov.get("mtf_retest_timestamp"))
