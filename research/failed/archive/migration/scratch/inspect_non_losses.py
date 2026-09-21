import json
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

with open("scratch/exp_c1_dev.json") as f:
    c1 = json.load(f)

trades = c1["all_trades"]
non_losses = [(i, t) for i, t in enumerate(trades) if t.get("net_r", 0) >= -0.001]

print(f"Non-losing trades in C1: {len(non_losses)} (2 Winners + 7 Breakevens)\n")

for orig_idx, t in non_losses:
    sym = t["symbol"]
    tf_set_id = t["timeframe_set"]
    tf_info = TimeframeAligner.get_set(tf_set_id)
    net_r = t["net_r"]
    mfe_r = t.get("mfe_r", 0.0)
    exit_reason = t["exit_reason"]
    meta = t.get("metadata", {})
    p = meta.get("structural_provenance", {})
    direction = t["directional_permission"]
    is_long = direction == "PERMIT_LONG"
    
    # Load MTF candles
    entry_ts = t["entry_timestamp"]
    candles = WarehouseLoader.load_history(sym, tf_info.mtf, limit=100, end_time_ms=entry_ts*1000)
    mtf_10bar_ret = 0.0
    with_trend = False
    if len(candles) >= 10:
        c_entry = candles[-1]
        c_prior10 = candles[-10]
        mtf_10bar_ret = (c_entry.close - c_prior10.close) / c_prior10.close * 100
        with_trend = (mtf_10bar_ret > 0) if is_long else (mtf_10bar_ret < 0)
        
    mtf_event = p.get("mtf_structural_event", "UNKNOWN").replace("EventType.", "")
    ltf_reason = p.get("ltf_entry_reason", "UNKNOWN").replace("_CONFIRMED", "")
    htf_target = p.get("htf_target_provenance", "UNKNOWN")
    raw_rr = t.get("raw_rr", 0.0)
    
    print(f"Trade #{orig_idx:02d} [{sym} {tf_set_id}] {'LONG' if is_long else 'SHRT'}: exit={exit_reason:15s} net_r={net_r:+7.4f} MFE={mfe_r:5.2f}R | MTF={mtf_event:15s} MTF_Mom={mtf_10bar_ret:+6.2f}% (with={with_trend}) | LTF={ltf_reason:25s} | Plan RR={raw_rr:5.2f}R")
