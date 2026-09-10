import os
import sys
import json
from collections import defaultdict
from datetime import datetime, timezone

with open("scratch/composite_01_dev_results_repaired_terminal.json") as f:
    replay_data = json.load(f)

streams = replay_data.get("stream_results", [])
all_trades = replay_data.get("all_trades", [])

print(f"Total streams loaded: {len(streams)}")
print(f"Total executed trades: {len(all_trades)}")

# 1. Per-Stream Detailed Metrics
stream_metrics = {}

for s in streams:
    sid = s.get("stream_id")
    asset = s.get("asset")
    tf_set = s.get("timeframe_set")
    status = s.get("status")
    trades = s.get("trades", [])
    cands = s.get("all_candidates", [])
    
    n_cands = len(cands)
    n_htf = sum(1 for c in cands if "HTF_QUALIFIED" in c.get("stages_reached", []))
    n_mtf_align = sum(1 for c in cands if "WAIT_MTF_RETEST" in c.get("stages_reached", []))
    n_mtf_retest = sum(1 for c in cands if "WAIT_LTF_TRIGGER" in c.get("stages_reached", []))
    n_ltf_confirmed = sum(1 for c in cands if c.get("ltf_confirmation_timestamp") is not None and c.get("ltf_confirmation_timestamp") > 0)
    
    # Target resolved: target exists and is valid
    n_target_resolved = 0
    n_rr_ge_4r = 0
    
    for c in cands:
        tp = c.get("htf_target_price")
        ep = c.get("ltf_entry_price")
        sl = c.get("ltf_structural_sl")
        if tp is not None and tp > 0 and ep is not None and sl is not None:
            stop_dist = abs(ep - sl)
            target_dist = abs(tp - ep)
            if stop_dist > 0:
                rr = target_dist / stop_dist
                n_target_resolved += 1
                if rr >= 4.0:
                    n_rr_ge_4r += 1

    # Trade stats
    n_trades = len(trades)
    wins = sum(1 for t in trades if t.get("net_r", 0) > 0)
    losses = sum(1 for t in trades if t.get("net_r", 0) <= 0)
    win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0
    net_r = sum(t.get("net_r", 0) for t in trades)
    gross_r = sum(t.get("gross_r", 0) for t in trades)
    friction_r = sum(t.get("fees_r", 0) + t.get("slippage_r", 0) for t in trades)
    
    pos_pnl = sum(t.get("net_r", 0) for t in trades if t.get("net_r", 0) > 0)
    neg_pnl = abs(sum(t.get("net_r", 0) for t in trades if t.get("net_r", 0) < 0))
    pf = (pos_pnl / neg_pnl) if neg_pnl > 0 else (999.0 if pos_pnl > 0 else 0.0)
    expectancy = (net_r / n_trades) if n_trades > 0 else 0.0
    
    # Max drawdown in R
    peak = 0.0
    cum = 0.0
    max_dd = 0.0
    for t in trades:
        cum += t.get("net_r", 0)
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd:
            max_dd = dd

    stream_metrics[sid] = {
        "stream_id": sid,
        "asset": asset,
        "tf_set": tf_set,
        "status": status,
        "candidates_total": n_cands,
        "htf_qualified": n_htf,
        "mtf_aligned": n_mtf_align,
        "mtf_retested": n_mtf_retest,
        "ltf_confirmed": n_ltf_confirmed,
        "target_resolved": n_target_resolved,
        "rr_ge_4r": n_rr_ge_4r,
        "executed_trades": n_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "net_r": net_r,
        "gross_r": gross_r,
        "friction_r": friction_r,
        "profit_factor": pf,
        "expectancy": expectancy,
        "max_drawdown_r": max_dd
    }

# Print 15-Stream Table Matrix
print("\n" + "=" * 140)
print(f"{'Stream ID':<10} | {'Status':<12} | {'Cands':<6} | {'HTF':<5} | {'MTF-Al':<6} | {'MTF-Rt':<6} | {'LTF-Cf':<6} | {'Tgt-Res':<7} | {'RR>=4R':<6} | {'Trades':<6} | {'Win%':<6} | {'Net R':<8} | {'PF':<6} | {'MaxDD':<6}")
print("=" * 140)

# Sort logically: SET_1 to SET_5, then BTC, ETH, SOL
tf_order = {"SET_1": 1, "SET_2": 2, "SET_3": 3, "SET_4": 4, "SET_5": 5}
asset_order = {"BTC": 1, "ETH": 2, "SOL": 3}
sorted_sids = sorted(stream_metrics.keys(), key=lambda sid: (tf_order.get(stream_metrics[sid]["tf_set"], 99), asset_order.get(stream_metrics[sid]["asset"], 99)))

for sid in sorted_sids:
    m = stream_metrics[sid]
    st_label = "FAIL_CLOSED" if "FAIL_CLOSED" in m["status"] else "OK"
    pf_str = f"{m['profit_factor']:.2f}" if m['profit_factor'] < 900 else "N/A"
    print(f"{m['stream_id']:<10} | {st_label:<12} | {m['candidates_total']:<6} | {m['htf_qualified']:<5} | {m['mtf_aligned']:<6} | {m['mtf_retested']:<6} | {m['ltf_confirmed']:<6} | {m['target_resolved']:<7} | {m['rr_ge_4r']:<6} | {m['executed_trades']:<6} | {m['win_rate']:<6.1f} | {m['net_r']:<+8.4f} | {pf_str:<6} | {m['max_drawdown_r']:<6.4f}")

# 2. Aggregations by Timeframe Set
print("\n" + "=" * 110)
print("AGGREGATION BY TIMEFRAME SET")
print("=" * 110)
print(f"{'Set ID':<8} | {'Style':<18} | {'Cands':<7} | {'LTF-Cf':<7} | {'RR>=4R':<7} | {'Trades':<7} | {'Win%':<7} | {'Net R':<10} | {'Expectancy':<10} | {'PF':<6}")
print("-" * 110)

tf_styles = {
    "SET_1": "1M/1W/1D (Macro)",
    "SET_2": "1W/1D/4H (Position)",
    "SET_3": "1D/4H/1H (Swing)",
    "SET_4": "4H/1H/15M (Intraday)",
    "SET_5": "15M/5M/1M (Scalping)"
}

for set_id in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
    set_streams = [m for m in stream_metrics.values() if m["tf_set"] == set_id]
    tot_cands = sum(m["candidates_total"] for m in set_streams)
    tot_ltf = sum(m["ltf_confirmed"] for m in set_streams)
    tot_rr = sum(m["rr_ge_4r"] for m in set_streams)
    tot_trades = sum(m["executed_trades"] for m in set_streams)
    tot_wins = sum(m["wins"] for m in set_streams)
    tot_losses = sum(m["losses"] for m in set_streams)
    win_rate = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
    net_r = sum(m["net_r"] for m in set_streams)
    exp = (net_r / tot_trades) if tot_trades > 0 else 0.0
    
    pos_p = sum(t["net_r"] for t in all_trades if t.get("timeframe_set") == set_id and t.get("net_r", 0) > 0)
    neg_p = abs(sum(t["net_r"] for t in all_trades if t.get("timeframe_set") == set_id and t.get("net_r", 0) < 0))
    pf = (pos_p / neg_p) if neg_p > 0 else (999.0 if pos_p > 0 else 0.0)
    pf_str = f"{pf:.2f}" if pf < 900 else ("inf" if pos_p > 0 else "0.00")
    
    print(f"{set_id:<8} | {tf_styles[set_id]:<18} | {tot_cands:<7} | {tot_ltf:<7} | {tot_rr:<7} | {tot_trades:<7} | {win_rate:<7.1f} | {net_r:<+10.4f} | {exp:<+10.4f} | {pf_str:<6}")

# 3. Aggregations by Asset
print("\n" + "=" * 110)
print("AGGREGATION BY ASSET")
print("=" * 110)
print(f"{'Asset':<8} | {'Cands':<7} | {'LTF-Cf':<7} | {'RR>=4R':<7} | {'Trades':<7} | {'Win%':<7} | {'Net R':<10} | {'Expectancy':<10} | {'PF':<6}")
print("-" * 110)

for asset in ["BTC", "ETH", "SOL"]:
    ast_streams = [m for m in stream_metrics.values() if m["asset"] == asset]
    tot_cands = sum(m["candidates_total"] for m in ast_streams)
    tot_ltf = sum(m["ltf_confirmed"] for m in ast_streams)
    tot_rr = sum(m["rr_ge_4r"] for m in ast_streams)
    tot_trades = sum(m["executed_trades"] for m in ast_streams)
    tot_wins = sum(m["wins"] for m in ast_streams)
    win_rate = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
    net_r = sum(m["net_r"] for m in ast_streams)
    exp = (net_r / tot_trades) if tot_trades > 0 else 0.0
    
    pos_p = sum(t["net_r"] for t in all_trades if t.get("symbol", "").startswith(asset) and t.get("net_r", 0) > 0)
    neg_p = abs(sum(t["net_r"] for t in all_trades if t.get("symbol", "").startswith(asset) and t.get("net_r", 0) < 0))
    pf = (pos_p / neg_p) if neg_p > 0 else (999.0 if pos_p > 0 else 0.0)
    pf_str = f"{pf:.2f}" if pf < 900 else ("inf" if pos_p > 0 else "0.00")
    
    print(f"{asset:<8} | {tot_cands:<7} | {tot_ltf:<7} | {tot_rr:<7} | {tot_trades:<7} | {win_rate:<7.1f} | {net_r:<+10.4f} | {exp:<+10.4f} | {pf_str:<6}")

# 4. Aggregations by Year
print("\n" + "=" * 110)
print("AGGREGATION BY CALENDAR YEAR")
print("=" * 110)
t_2021 = [t for t in all_trades if datetime.fromtimestamp(t.get("entry_timestamp", 0), tz=timezone.utc).year == 2021]
t_2022 = [t for t in all_trades if datetime.fromtimestamp(t.get("entry_timestamp", 0), tz=timezone.utc).year == 2022]

for yr, trs in [("2021", t_2021), ("2022", t_2022)]:
    n_t = len(trs)
    n_w = sum(1 for t in trs if t.get("net_r", 0) > 0)
    wr = (n_w / n_t * 100.0) if n_t > 0 else 0.0
    net_r = sum(t.get("net_r", 0) for t in trs)
    exp = (net_r / n_t) if n_t > 0 else 0.0
    pos_p = sum(t.get("net_r", 0) for t in trs if t.get("net_r", 0) > 0)
    neg_p = abs(sum(t.get("net_r", 0) for t in trs if t.get("net_r", 0) < 0))
    pf = (pos_p / neg_p) if neg_p > 0 else (999.0 if pos_p > 0 else 0.0)
    print(f"Year {yr}: {n_t:2d} trades | Win Rate: {wr:5.1f}% | Net R: {net_r:+8.4f}R | Expectancy: {exp:+8.4f}R | Profit Factor: {pf:.2f}")

# Save json summary
with open("scratch/full_baseline_architecture_summary.json", "w") as fp:
    json.dump({
        "stream_metrics": stream_metrics,
        "total_trades": len(all_trades),
        "total_candles_evaluated": 277908
    }, fp, indent=2)
