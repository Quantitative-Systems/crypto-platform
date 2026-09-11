import os, json
from research.replayer.timeframe_aligner import TimeframeAligner
from market_data.warehouse_loader import WarehouseLoader
from research.experiments.run_canonical_replay_engine import TF_SET_METADATA

with open('scratch/h0_dev_certified_results.json') as f:
    h0 = json.load(f)

for t in h0['all_trades']:
    stream = t['stream_id']
    entry_ts = t['entry_timestamp']
    exit_ts = t['exit_timestamp']
    symbol = t['symbol']
    tf_set = t['timeframe_set']
    tf_info = TF_SET_METADATA[tf_set]
    ltf = tf_info['ltf']

    print(f"\n=======================================================")
    print(f"--- {stream} {t['trade_id']} ---")
    print(f"Entry: {entry_ts}, Exit: {exit_ts}, Direction: {t['direction']}, Entry P: {t['entry_price']}, Init SL: {t['initial_stop_price']}")
    init_sl = t['initial_stop_price']
    entry = t['entry_price']
    risk = abs(entry - init_sl)
    p_05 = entry + 0.5 * risk if t['direction'] == 'LONG' else entry - 0.5 * risk
    p_025 = entry + 0.25 * risk if t['direction'] == 'LONG' else entry - 0.25 * risk
    print(f"Risk: {risk:.2f}, +0.5R level: {p_05:.2f}, +0.25R level: {p_025:.2f}")

    candles = WarehouseLoader.load_history(symbol, ltf, limit=1_000_000, start_time_ms=entry_ts*1000, end_time_ms=(exit_ts+3600*24)*1000)
    for c in candles[:8]:
        ts = c.timestamp if c.timestamp < 1e11 else c.timestamp // 1000
        o, h, l, cl = c.open, c.high, c.low, c.close
        fav_r = (h - entry) / risk if t['direction'] == 'LONG' else (entry - l) / risk
        adv_r = (entry - l) / risk if t['direction'] == 'LONG' else (h - entry) / risk
        close_r = (cl - entry) / risk if t['direction'] == 'LONG' else (entry - cl) / risk
        is_entry = (ts == entry_ts)
        print(f"  Bar ts={ts} {'(ENTRY)' if is_entry else '       '}: O={o:.2f} H={h:.2f} L={l:.2f} C={cl:.2f} | fav={fav_r:+.2f}R adv={adv_r:+.2f}R close_r={close_r:+.2f}R")
