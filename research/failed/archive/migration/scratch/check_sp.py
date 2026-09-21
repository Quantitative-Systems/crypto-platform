import json

with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

for i, t in enumerate(e1["all_trades"]):
    meta = t.get("metadata", {})
    sp1 = meta.get("sweep_provenance")
    sp2 = meta.get("structural_provenance", {}).get("sweep_provenance")
    print(f"Trade {i+1}: {t['trade_id']} | sp1: {bool(sp1)} | sp2: {bool(sp2)}")
    if sp2:
        print("   sp2:", sp2)
