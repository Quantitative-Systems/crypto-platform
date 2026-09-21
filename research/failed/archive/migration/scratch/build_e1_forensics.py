import json
import os
import sys
import numpy as np

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trades = d1["all_trades"]
e1_trades = e1["all_trades"]

print(f"D1 total trades: {len(d1_trades)}")
print(f"E1 total trades: {len(e1_trades)}")

print("\n=== E1 TRADES SWEEP PROVENANCE ===")
for i, t in enumerate(e1_trades):
    sp = t.get("metadata", {}).get("sweep_provenance", {})
    struct_p = t.get("metadata", {}).get("structural_provenance", {})
    print(f"[{i+1:02d}] {t['trade_id']} | {t['symbol']} | {t['timeframe_set']} | {t['direction']} | Net R: {t['net_r']:+.4f} | Exit: {t['exit_reason']}")
    print(f"     Entry TS: {t['entry_timestamp']} | Price: {t['entry_price']} | SL: {t['initial_stop_price']} | TP: {t['target_price']} | RR: {t['raw_rr']:.2f}R")
    if sp:
        print(f"     Sweep Provenance:")
        print(f"       Swept Swing TS:        {sp.get('swept_ltf_swing_timestamp')}")
        print(f"       Swept Swing Price:     {sp.get('swept_swing_price')}")
        print(f"       Sweep Direction:       {sp.get('sweep_direction')}")
        print(f"       Sweep Conf TS:         {sp.get('sweep_confirmation_timestamp')}")
        print(f"       Displacement Conf TS:  {sp.get('displacement_confirmation_timestamp')}")
        print(f"       Bars Between:          {sp.get('number_of_ltf_bars_between')}")
        print(f"       MTF Retest TS:         {sp.get('mtf_retest_timestamp')}")
        print(f"       Sweep After Retest:    {sp.get('sweep_occurred_causally_after_retest')}")
    else:
        print(f"     NO SWEEP PROVENANCE IN METADATA! struct_p={struct_p.get('ltf_entry_reason')}")
