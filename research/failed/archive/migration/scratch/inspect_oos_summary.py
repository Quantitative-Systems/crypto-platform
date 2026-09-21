import json

with open("/home/mrcn2/crypto-platform/scratch/gate5_oos_validation_results.json", "r") as f:
    data = json.load(f)

print("=" * 115)
print(f"{'Stream':<24} | {'IS Trd':<6} | {'IS WR%':<7} | {'IS PF':<6} | {'IS ExpR':<8} | {'OOS Trd':<7} | {'OOS WR%':<8} | {'OOS PF':<7} | {'OOS ExpR':<8} | {'Status':<16}")
print("-" * 115)

for s in data:
    sym = s["symbol"]
    set_id = s["tf_set_id"]
    st = s["status"]
    is_c = s["is_stats"]["combined"]
    oos_c = s["oos_stats"]["combined"]
    print(f"{sym+' '+set_id:<24} | {is_c['total_trades']:<6} | {is_c['win_rate_pct']:<6.1f}% | {is_c['profit_factor']:<6.2f} | {is_c['expectancy_r']:<+7.2f}R | {oos_c['total_trades']:<7} | {oos_c['win_rate_pct']:<7.1f}% | {oos_c['profit_factor']:<7.2f} | {oos_c['expectancy_r']:<+7.2f}R | {st:<16}")
