import json

with open("scratch/canonical_rebuild_dev_results.json") as f:
    d = json.load(f)

trades = d["trade_ledger"]
print(f"Total Trades: {len(trades)}")
print(f"{'Symbol':<10} | {'Set':<6} | {'Dir':<6} | {'Entry':<9} | {'SL':<9} | {'Dist%':<6} | {'Target':<9} | {'PlanRR':<6} | {'MFE_R':<6} | {'ExitReason':<22} | {'NetR':<6}")
print("-" * 115)
for t in trades:
    entry = t["entry_price"]
    sl = t["initial_stop_price"]
    dist_pct = abs(entry - sl) / entry * 100
    tgt = t["target_price"]
    plan_rr = t["raw_rr"]
    mfe_r = t.get("mfe_r", 0.0)
    reason = t.get("exit_reason", "")
    net_r = t.get("net_r", 0.0)
    sym = t["symbol"]
    tset = t["timeframe_set"]
    dir_str = t["direction"]
    print(f"{sym:<10} | {tset:<6} | {dir_str:<6} | {entry:<9.2f} | {sl:<9.2f} | {dist_pct:<5.2f}% | {tgt:<9.2f} | {plan_rr:<6.2f} | {mfe_r:<6.2f} | {reason:<22} | {net_r:<6.2f}")
