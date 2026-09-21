import json

with open("scratch/exp_d1_dev.json") as f:
    d1 = json.load(f)
with open("scratch/exp_e1_dev.json") as f:
    e1 = json.load(f)

d1_trade_ids = {t["trade_id"] for t in d1["all_trades"]}

e1_new_trades = [t for t in e1["all_trades"] if t["trade_id"] not in d1_trade_ids]
print(f"E1 new trades count: {len(e1_new_trades)}")

# Find their candidates in d1 stream_results
for t in e1_new_trades:
    cid = t["trade_id"]
    sym = t["symbol"]
    st = t["timeframe_set"]
    print(f"\nE1 Trade: {cid} | {sym} {st} | ts={t['entry_timestamp']} | pnl={t['net_r']:+.4f}R")
    # find in d1 stream
    for s in d1["stream_results"]:
        s_sym = s.get("symbol") or f"{s.get('asset')}/USDT"
        if s_sym == sym and s.get("timeframe_set") == st:
            cands = [c for c in s.get("all_candidates", []) if c.get("candidate_id") == cid]
            if cands:
                c = cands[0]
                print(f"  In D1 candidate record: state={c.get('state')} stages={c.get('stages_reached')} inv_reason={c.get('invalidation_reason')}")
            else:
                print(f"  In D1 candidate record: NOT FOUND in all_candidates (total={len(s.get('all_candidates', []))})")
