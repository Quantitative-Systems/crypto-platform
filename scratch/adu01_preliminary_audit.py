import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

trades = d1["all_trades"]
print("Total D1 Trades:", len(trades))
print("-" * 110)

wins = []
bes = []
trails = []
stopouts = []

for i, t in enumerate(trades):
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    dir_ = t["direction"]
    entry_ts = t["entry_timestamp"]
    net_r = t["net_r"]
    exit_r = t["exit_reason"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    sp = t.get("metadata", {}).get("structural_provenance", {})
    trig = sp.get("ltf_entry_reason")
    mtf_event = sp.get("mtf_structural_event")
    htf_phase = sp.get("htf_phase")
    retest_ts = sp.get("mtf_retest_timestamp")
    align_ts = sp.get("mtf_alignment_timestamp")
    retest_latency_hrs = (retest_ts - align_ts) / 3600.0 if (retest_ts and align_ts) else 0.0
    
    rec = {
        "idx": i + 1, "id": cid, "sym": sym, "set": st, "dir": dir_, "ts": entry_ts,
        "net_r": net_r, "exit": exit_r, "mfe": mfe, "mae": mae, "trig": trig,
        "mtf": mtf_event, "phase": htf_phase, "latency": retest_latency_hrs,
        "raw_rr": t.get("raw_rr", 0.0)
    }
    
    if net_r > 0.05:
        wins.append(rec)
    elif abs(net_r) <= 0.05:
        bes.append(rec)
    elif "TRAIL" in exit_r:
        trails.append(rec)
    else:
        stopouts.append(rec)

print(f"WINS ({len(wins)}):")
for r in wins:
    print(f"  [{r['idx']:02d}] {r['sym']} {r['set']} {r['dir']} | Net={r['net_r']:+.4f}R | MFE={r['mfe']:.2f}R | Exit={r['exit']} | MTF={r['mtf']} | Latency={r['latency']:.1f}h | Trig={r['trig']}")

print(f"\nBREAKEVENS ({len(bes)}):")
for r in bes:
    print(f"  [{r['idx']:02d}] {r['sym']} {r['set']} {r['dir']} | Net={r['net_r']:+.4f}R | MFE={r['mfe']:.2f}R | Exit={r['exit']} | MTF={r['mtf']} | Latency={r['latency']:.1f}h | Trig={r['trig']}")

print(f"\nTRAILED SCRATCHES ({len(trails)}):")
for r in trails:
    print(f"  [{r['idx']:02d}] {r['sym']} {r['set']} {r['dir']} | Net={r['net_r']:+.4f}R | MFE={r['mfe']:.2f}R | Exit={r['exit']} | MTF={r['mtf']} | Latency={r['latency']:.1f}h | Trig={r['trig']}")

print(f"\nFULL STOP-OUTS ({len(stopouts)}):")
for r in stopouts:
    print(f"  [{r['idx']:02d}] {r['sym']} {r['set']} {r['dir']} | Net={r['net_r']:+.4f}R | MFE={r['mfe']:.2f}R | Exit={r['exit']} | MTF={r['mtf']} | Latency={r['latency']:.1f}h | Trig={r['trig']}")
