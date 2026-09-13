import json

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

trades = c1["all_trades"]
print("Total trades in C1:", len(trades))

filtered = []
for t in trades:
    p = t.get("metadata", {}).get("structural_provenance", {})
    ev = p.get("mtf_structural_event", "").replace("EventType.", "")
    if ev != "INTERNAL_CHOCH":
        filtered.append(t)
    else:
        sym = t.get("symbol")
        tf = t.get("timeframe_set")
        ex = t.get("exit_reason")
        nr = t.get("net_r")
        print("Filtered out: [{}_{}] exit={:<20} net_r={:+.4f}".format(sym, tf, ex, nr))

print("\nRemaining trades:", len(filtered))
wins = [t for t in filtered if t["exit_reason"] == "HTF_TP"]
bes = [t for t in filtered if t["exit_reason"] == "BREAKEVEN_TRAIL"]
losses = [t for t in filtered if t["exit_reason"] not in ["HTF_TP", "BREAKEVEN_TRAIL"]]
net_r = sum(t["net_r"] for t in filtered)
print("Wins: {}, BE: {}, Losses: {}".format(len(wins), len(bes), len(losses)))
print("Net R: {:+.4f}R (vs C1 Net R = -6.1605R)".format(net_r))
