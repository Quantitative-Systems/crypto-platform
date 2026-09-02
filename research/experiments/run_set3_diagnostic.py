import json
from research.experiments.run_phase3_baseline import run_single_stream_baseline

print("=" * 90)
print("PHASE 3 / STEP 7: SET_3 DIAGNOSTIC REPLAY (BTC/USDT: 1D -> 4H -> 1H)")
print("=" * 90)

res = run_single_stream_baseline(symbol="BTC/USDT", timeframe_set_id="SET_3")

print("\n[STREAM]:", res["symbol"], "|", res["timeframe_set_id"], f"({res['timeframe_set']['description']})")
print("[PERIOD]:", res["period"]["start"], "->", res["period"]["end"], f"({res['period']['total_days']:.1f} days)")
print("[CANDLES]:", res["candles_processed"])
print(f"[EXECUTION TIME]: {res['execution_time_sec']:.2f}s")

print("\n" + "=" * 50)
print("LIFECYCLE FUNNEL TELEMETRY (SET_3)")
print("=" * 50)
for stage, cnt in res["funnel_counts"].items():
    print(f"  {stage:30s}: {cnt:5d}")

print("\nREJECTION BREAKDOWN (SET_3):")
for reason, cnt in res["rejection_breakdown"].items():
    print(f"  {reason:40s}: {cnt:5d}")

print("\n" + "=" * 50)
print("BASELINE PERFORMANCE METRICS (SET_3)")
print("=" * 50)
m = res["baseline_metrics"]
for k, v in m.items():
    if k != "r_multiples":
        print(f"  {k:30s}: {v}")

print("\n" + "=" * 50)
print("EXIT ATTRIBUTION (SET_3)")
print("=" * 50)
for cat, data in res["exit_attribution"].items():
    print(f"  {cat:25s} -> Count: {data['trade_count']:3d} ({data['percentage_of_total']*100:5.1f}%) | WR: {data['win_rate']*100:5.1f}% | Avg R: {data['avg_realized_r']:+5.2f}R | Total PnL: ${data['total_pnl_usd']:+8.2f}")

print("\n" + "=" * 50)
print(f"CLOSED TRADES ({len(res['closed_trades'])})")
print("=" * 50)
for idx, t in enumerate(res["closed_trades"], 1):
    print(f"  [{idx:02d}] {t['trade_id']} | Dir: {t['directional_permission']:12s} | Entry: {t['entry_price']} -> Exit: {t['exit_price']} | Net R: {t['net_r']:+5.2f}R | Net PnL: ${t['net_pnl']:+8.2f} | Reason: {t['exit_reason']}")

with open("/home/mrcn2/crypto-platform/scratch/set3_diagnostic_results.json", "w") as f:
    json.dump(res, f, indent=2)
print("\n✅ Saved Set 3 diagnostic results to /home/mrcn2/crypto-platform/scratch/set3_diagnostic_results.json")
