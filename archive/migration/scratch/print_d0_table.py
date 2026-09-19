import json

with open("scratch/d0_forensic_records.json") as f:
    recs = json.load(f)

headers = ["#", "Trade", "Dir", "Net R", "MFE(R)", "Cat", "Timing", "Exit Behavior", "MTF Event", "MTF Disp", "LTF Trigger", "Plan RR"]
row_fmt = "{:<2} | {:<16} | {:<5} | {:>7} | {:>6} | {:<8} | {:<10} | {:<32} | {:<14} | {:>8} | {:<30} | {:>7}"

print(row_fmt.format(*headers))
print("-" * 165)

for r in recs:
    idx_str = f"T{r['orig_trade_idx']:02d} {r['symbol'].split('/')[0]} {r['tf_set']}"
    dir_str = "LONG" if "LONG" in r["direction"] else "SHRT"
    timing_str = r["mfe_timing"].split()[0]
    ltf_short = r["ltf_trigger_reason"].replace("_CONFIRMED", "").replace("DISPLACEMENT", "DISP")
    print(row_fmt.format(
        r["rank"],
        idx_str,
        dir_str,
        f"{r['net_r']:.4f}",
        f"{r['mfe_r']:.2f}",
        r["mfe_cat"],
        timing_str,
        r["exit_behavior"],
        r["mtf_event"],
        f"{r['mtf_displacement_pct']:.2f}%",
        ltf_short,
        f"{r['raw_rr']:.2f}R"
    ))
