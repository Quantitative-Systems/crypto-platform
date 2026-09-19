"""
Inspect regime forensics across all 24 streams.
"""

import json

with open("/home/mrcn2/crypto-platform/scratch/gate5b_24_stream_forensic_results.json", "r") as f:
    bundle = json.load(f)

control = bundle["control_baseline_24_streams"]

print("=" * 100)
print("SECTION 9: REGIME & MARKET CONDITION FORENSICS")
print("=" * 100)

agg_regimes = {}

for s in control:
    cm = s["combined"]["metrics"]
    for reg_k, reg_v in cm.get("regime_breakdown", {}).items():
        if reg_k not in agg_regimes:
            agg_regimes[reg_k] = {"trades": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0}
        agg_regimes[reg_k]["trades"] += reg_v["trades"]
        agg_regimes[reg_k]["wins"] += reg_v["wins"]
        agg_regimes[reg_k]["pnl"] += reg_v["pnl"]
        agg_regimes[reg_k]["r_sum"] += reg_v["r_sum"]

print(f"{'HTF Macro Trend | HTF Phase':<45} | {'Trades':<6} | {'WR (%)':<7} | {'Net PnL ($)':<14} | {'Total R':<10} | {'Avg R':<7}")
print("-" * 100)
for k, v in sorted(agg_regimes.items(), key=lambda x: x[1]["trades"], reverse=True):
    wr = (v["wins"] / v["trades"] * 100.0) if v["trades"] > 0 else 0.0
    avg_r = (v["r_sum"] / v["trades"]) if v["trades"] > 0 else 0.0
    print(f"{k:<45} | {v['trades']:<6} | {wr:<7.2f} | ${v['pnl']:<13,.2f} | {v['r_sum']:<+9.2f}R | {avg_r:<+6.2f}R")
