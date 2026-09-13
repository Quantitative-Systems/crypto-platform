import json

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

t16 = c1["all_trades"][16]
print("Trade 16 trade_id:", t16["trade_id"])
print("Trade 16 symbol:", t16["symbol"], "tf:", t16["timeframe_set"])
meta = t16.get("metadata", {})
p = meta.get("structural_provenance", {})
print("ltf_entry_reason:", p.get("ltf_entry_reason"))
print("Full provenance:")
for k, v in p.items():
    print(" ", k, ":", v)
