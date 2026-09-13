import json
from datetime import datetime, timezone

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

with open("scratch/canonical_h0_corrected_dev_results.json") as f:
    h0 = json.load(f)

print("=== 1. COMPARATIVE PERFORMANCE: H0 vs C1 vs D1 ===")
print(f"{'Metric':<28} | {'H0 (Canonical)':<16} | {'C1 (Milestone)':<16} | {'D1 (Major MTF)':<16}")
print("-" * 82)
for k in ["total_trades", "win_rate", "net_r", "expectancy", "profit_factor", "max_drawdown_r", "median_mfe_r", "median_mae_r"]:
    val_h0 = h0["aggregate_performance"].get(k, "N/A")
    val_c1 = c1["aggregate_performance"].get(k, "N/A")
    val_d1 = d1["aggregate_performance"].get(k, "N/A")
    print(f"{k:<28} | {str(val_h0):<16} | {str(val_c1):<16} | {str(val_d1):<16}")

trades_d1 = d1["all_trades"]
trades_c1 = c1["all_trades"]

print(f"\n=== 2. D1 EXECUTED TRADE LEDGER (N={len(trades_d1)}) ===")
print(f"{'#':<3} | {'Asset':<8} | {'Set':<10} | {'Dir':<5} | {'Net R':<9} | {'MFE R':<7} | {'MAE R':<7} | {'MTF Event':<26} | {'LTF Reason':<28} | {'Exit Reason':<22}")
print("-" * 140)
for i, t in enumerate(trades_d1):
    sym = t.get("symbol", "")
    stream = t.get("stream_id", "")
    direction = t.get("direction", "")
    net_r = t.get("net_r", 0.0)
    mfe = t.get("mfe_r", 0.0)
    mae = t.get("mae_r", 0.0)
    exit_r = t.get("exit_reason", "")
    prov = t.get("metadata", {}).get("structural_provenance", {})
    event = prov.get("mtf_structural_event", "").replace("EventType.", "")
    ltf_reason = prov.get("ltf_entry_reason", "")
    print(f"{i:02d}  | {sym:<8} | {stream:<10} | {direction:<5} | {net_r:+8.4f}R | {mfe:6.2f}R | {mae:6.2f}R | {event:<26} | {ltf_reason:<28} | {exit_r:<22}")

# Check winners
print("\n=== 3. STRUCTURAL PRESERVATION OF OBSERVED WINNERS ===")
winners_d1 = [t for t in trades_d1 if t.get("net_r", 0.0) > 1.0]
print(f"Total winners in D1: {len(winners_d1)}")
for w in winners_d1:
    print(f"  * {w.get('symbol')} {w.get('stream_id')} {w.get('direction')} Net R: {w.get('net_r'):+.4f}R | MFE: {w.get('mfe_r'):.2f}R | Exit: {w.get('exit_reason')}")

# Distribution comparison
def calc_dist(trades):
    mfes = [t.get("mfe_r", 0.0) for t in trades]
    n = len(mfes)
    return {
        "< 0.5R": f"{sum(1 for m in mfes if m < 0.5)}/{n} ({sum(1 for m in mfes if m < 0.5)/n*100:.1f}%)",
        "0.5R-1.0R": f"{sum(1 for m in mfes if 0.5 <= m < 1.0)}/{n} ({sum(1 for m in mfes if 0.5 <= m < 1.0)/n*100:.1f}%)",
        "1.0R-1.5R": f"{sum(1 for m in mfes if 1.0 <= m < 1.5)}/{n} ({sum(1 for m in mfes if 1.0 <= m < 1.5)/n*100:.1f}%)",
        "1.5R-2.0R": f"{sum(1 for m in mfes if 1.5 <= m < 2.0)}/{n} ({sum(1 for m in mfes if 1.5 <= m < 2.0)/n*100:.1f}%)",
        ">= 2.0R": f"{sum(1 for m in mfes if m >= 2.0)}/{n} ({sum(1 for m in mfes if m >= 2.0)/n*100:.1f}%)"
    }

dist_c1 = calc_dist(trades_c1)
dist_d1 = calc_dist(trades_d1)

print("\n=== 4. MFE EXCURSION DISTRIBUTION COMPARISON ===")
print(f"{'Bracket':<15} | {'C1 (N=29)':<20} | {'D1 (N=24)':<20}")
print("-" * 60)
for k in dist_c1:
    print(f"{k:<15} | {dist_c1[k]:<20} | {dist_d1[k]:<20}")

# Event breakdown in D1
events_d1 = {}
for t in trades_d1:
    ev = t.get("metadata", {}).get("structural_provenance", {}).get("mtf_structural_event", "").replace("EventType.", "")
    events_d1[ev] = events_d1.get(ev, 0) + 1
print("\n=== 5. D1 MTF EVENT BREAKDOWN ===")
for ev, cnt in events_d1.items():
    print(f"  * {ev}: {cnt} trades ({cnt/len(trades_d1)*100:.1f}%)")

# Detailed comparison with C1: which trades changed?
print("\n=== 6. CAUSAL REPLAY LIFECYCLE DIFFERENCES (C1 vs D1) ===")
c1_ids = {(t["symbol"], t["stream_id"], t.get("entry_timestamp")): t for t in trades_c1}
d1_ids = {(t["symbol"], t["stream_id"], t.get("entry_timestamp")): t for t in trades_d1}

removed = set(c1_ids.keys()) - set(d1_ids.keys())
added = set(d1_ids.keys()) - set(c1_ids.keys())
common = set(c1_ids.keys()) & set(d1_ids.keys())

print(f"Trades in C1 but NOT in D1 (Filtered / Replaced): {len(removed)}")
for sym, st, ts in sorted(removed):
    t = c1_ids[(sym, st, ts)]
    ev = t.get("metadata", {}).get("structural_provenance", {}).get("mtf_structural_event", "").replace("EventType.", "")
    dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
    print(f"  - REMOVED: {sym} {st} at {dt_str} | Net R: {t.get('net_r'):+.4f}R | Event: {ev} | Exit: {t.get('exit_reason')}")

print(f"\nTrades in D1 but NOT in C1 (Newly Captured by Causal Realignment): {len(added)}")
for sym, st, ts in sorted(added):
    t = d1_ids[(sym, st, ts)]
    ev = t.get("metadata", {}).get("structural_provenance", {}).get("mtf_structural_event", "").replace("EventType.", "")
    dt_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ts else "N/A"
    print(f"  + NEW:     {sym} {st} at {dt_str} | Net R: {t.get('net_r'):+.4f}R | Event: {ev} | Exit: {t.get('exit_reason')}")

print(f"\nIdentical common trades preserved: {len(common)}")
