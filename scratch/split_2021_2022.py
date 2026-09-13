import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

trades = d1["all_trades"]
t_2021 = [t for t in trades if t["entry_timestamp"] < 1640995200]
t_2022 = [t for t in trades if t["entry_timestamp"] >= 1640995200]

print(f"2021 D1 Trades ({len(t_2021)}): Net R = {sum(t['net_r'] for t in t_2021):+.4f}R")
for t in t_2021:
    print(f"  {t['symbol']} {t['timeframe_set']} {t['direction']} | Net={t['net_r']:+.4f}R | MFE={t['mfe_r']:.2f}R | Exit={t['exit_reason']}")

print(f"\n2022 D1 Trades ({len(t_2022)}): Net R = {sum(t['net_r'] for t in t_2022):+.4f}R")
for t in t_2022:
    print(f"  {t['symbol']} {t['timeframe_set']} {t['direction']} | Net={t['net_r']:+.4f}R | MFE={t['mfe_r']:.2f}R | Exit={t['exit_reason']}")
