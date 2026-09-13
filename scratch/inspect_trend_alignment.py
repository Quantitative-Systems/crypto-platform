import json
from market_data.warehouse_loader import WarehouseLoader
from research.replayer.timeframe_aligner import TimeframeAligner

with open("scratch/d0_forensic_records.json") as f:
    recs = json.load(f)

for r in recs:
    sym = r["symbol"]
    tf_info = TimeframeAligner.get_set(r["tf_set"])
    entry_ts = r["entry_timestamp"]
    
    # Load MTF candles around entry
    candles = WarehouseLoader.load_history(sym, tf_info.mtf, limit=100, end_time_ms=entry_ts*1000)
    if len(candles) >= 10:
        c_entry = candles[-1]
        c_prior10 = candles[-10]
        mtf_10bar_ret = (c_entry.close - c_prior10.close) / c_prior10.close * 100
        is_long = "LONG" in r["direction"]
        with_trend = (mtf_10bar_ret > 0) if is_long else (mtf_10bar_ret < 0)
        print(f"Trade #{r['rank']:02d} [T{r['orig_trade_idx']:02d}] {sym} {r['tf_set']} {'LONG' if is_long else 'SHRT'}: MTF 10-bar Return = {mtf_10bar_ret:+.2f}% | With MTF Mom: {with_trend} | MFE: {r['mfe_r']:.2f}R | Net R: {r['net_r']:.4f}")
