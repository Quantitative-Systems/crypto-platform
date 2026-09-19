import json
from collections import Counter, defaultdict

with open("scratch/canonical_h0_corrected_dev_results.json") as f:
    d = json.load(f)

agg = d["aggregate_performance"]
trades = d["all_trades"]
print("=" * 80)
print("CORRECTED CANONICAL H0 BASELINE REPORT")
print("=" * 80)
print(f"Total Trades: {len(trades)}")
print(f"Wins: {agg['wins']}, Losses: {agg['losses']}, Breakevens: {agg['breakevens']}")
print(f"Win Rate: {agg['win_rate']:.1f}%")
print(f"Net R: {agg['net_r']:.4f}R, Gross R: {agg['gross_r']:.4f}R, Friction: {agg['friction_r']:.4f}R")
print(f"Expectancy: {agg['expectancy']:.4f}R")
print(f"Profit Factor: {agg['profit_factor']:.4f}")
print(f"Max Drawdown R: {agg['max_drawdown_r']:.4f}R")
print(f"Max Consecutive Losses: {agg['max_consecutive_losses']}")
print(f"Avg MFE: {agg['avg_mfe_r']:.4f}R, Median MFE: {agg['median_mfe_r']:.4f}R")
print(f"Avg MAE: {agg['avg_mae_r']:.4f}R, Median MAE: {agg['median_mae_r']:.4f}R")

# Breakdown by asset
by_asset = defaultdict(list)
by_tf = defaultdict(list)
exit_reasons = Counter()

for t in trades:
    asset = t.get("stream_id", "").split("_")[0]
    tf = "_".join(t.get("stream_id", "").split("_")[1:])
    by_asset[asset].append(t)
    by_tf[tf].append(t)
    exit_reasons[t.get("exit_reason", "UNKNOWN")] += 1

print("\n" + "-" * 40)
print("BREAKDOWN BY ASSET:")
print("-" * 40)
for a, trs in sorted(by_asset.items()):
    rs = [tr.get("realized_rr", 0.0) for tr in trs]
    wins = sum(1 for r in rs if r > 0)
    print(f"  {a:5s}: N={len(trs):2d} | Wins={wins:2d} | WinRate={wins/len(trs)*100:5.1f}% | Net R={sum(rs):8.4f}R | E[R]={sum(rs)/len(trs):8.4f}R")

print("\n" + "-" * 40)
print("BREAKDOWN BY TIMEFRAME SET:")
print("-" * 40)
for tf, trs in sorted(by_tf.items()):
    rs = [tr.get("realized_rr", 0.0) for tr in trs]
    wins = sum(1 for r in rs if r > 0)
    print(f"  {tf:10s}: N={len(trs):2d} | Wins={wins:2d} | WinRate={wins/len(trs)*100:5.1f}% | Net R={sum(rs):8.4f}R | E[R]={sum(rs)/len(trs):8.4f}R")

print("\n" + "-" * 40)
print("EXIT REASONS:")
print("-" * 40)
for er, cnt in exit_reasons.most_common():
    pct = (cnt / len(trades) * 100) if trades else 0
    print(f"  {er:30s}: {cnt:2d} ({pct:5.1f}%)")

# Candidates funnel across all streams
all_cand_states = Counter()
cand_rejections = Counter()
total_candidates = 0
for s in d["stream_results"]:
    cands = s.get("all_candidates", [])
    total_candidates += len(cands)
    for c in cands:
        all_cand_states[c.get("state", "UNKNOWN")] += 1
        if c.get("invalidation_reason"):
            cand_rejections[c.get("invalidation_reason")] += 1

print("\n" + "-" * 40)
print(f"CANDIDATES FUNNEL: Total = {total_candidates}")
print("-" * 40)
for st, cnt in all_cand_states.most_common():
    print(f"  State {st:25s}: {cnt:4d} ({cnt/total_candidates*100:5.1f}%)")

print("\nTop Candidate Invalidation Reasons:")
for ir, cnt in cand_rejections.most_common(10):
    print(f"  {ir:35s}: {cnt:4d} ({cnt/total_candidates*100:5.1f}%)")

# Trade details
print("\n" + "-" * 40)
print("INDIVIDUAL TRADE LEDGER:")
print("-" * 40)
for i, t in enumerate(trades):
    st_id = t.get("stream_id", "")
    direction = "LONG" if "LONG" in t.get("directional_permission", "") else "SHORT"
    ep = t.get("fill_entry_price", t.get("entry_price", 0.0))
    sl = t.get("initial_stop_price", 0.0)
    tp = t.get("target_price", 0.0)
    r_r = t.get("realized_rr", 0.0)
    mfe = t.get("mfe_r", 0.0)
    ex = t.get("exit_reason", "")
    raw_rr = t.get("raw_rr", 0.0)
    print(f"  Trade {i+1:2d} [{st_id:10s}]: {direction:5s} | Entry={ep:10.2f} | SL={sl:10.2f} | Target={tp:10.2f} | Planned RR={raw_rr:5.2f}R | Realized R={r_r:7.4f}R | MFE={mfe:5.2f}R | Exit={ex}")
