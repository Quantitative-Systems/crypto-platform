import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

for i in [8, 9, 10, 12, 13, 17]:
    t = d1["all_trades"][i]
    prov = t["metadata"]["structural_provenance"]
    sym = t["symbol"]
    st = t["stream_id"]
    r = prov.get("ltf_entry_reason")
    print(f"Trade {i}: symbol={sym}, stream={st}, reason={r}")
