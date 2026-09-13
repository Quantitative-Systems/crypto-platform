import json
from datetime import datetime, timezone

def ts_to_str(ts):
    if not ts:
        return "N/A"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

with open('scratch/canonical_h0_backtest_dev.json') as f:
    h0_data = json.load(f)

trades = h0_data['all_trades']

mfe_loss_trades = [t for t in trades if t.get('mfe_r', 0) >= 2.0 and t.get('net_r', 0) < 0]

print("=" * 100)
print("RECONSTRUCTION OF H0 TRADES WITH MFE >= 2.0R AND REALIZED R < 0")
print("=" * 100)

for idx, t in enumerate(mfe_loss_trades):
    tid = t['trade_id']
    sid = t['stream_id']
    direction = t['directional_permission']
    is_long = direction == "PERMIT_LONG"
    
    entry_ts = t['entry_timestamp']
    exit_ts = t['exit_timestamp']
    meta = t.get('metadata', {})
    mfe_ts = meta.get('mfe_timestamp', exit_ts)
    
    entry_p = t.get('fill_entry_price', t['entry_price'])
    stop_p = t['initial_stop_price']
    curr_stop = t['current_stop_price']
    target_p = t['target_price']
    exit_p = t['exit_price']
    
    risk_dist = abs(entry_p - stop_p)
    mfe_r = t['mfe_r']
    mae_r = t['mae_r']
    net_r = t['net_r']
    exit_reason = t['exit_reason']
    
    # Timeframe context
    # SET_2: HTF=1w, MTF=1d, LTF=4h
    # SET_3: HTF=1d, MTF=4h, LTF=1h
    # SET_4: HTF=4h, MTF=1h, LTF=15m
    mtf_tf = "4h" if "SET_3" in sid else ("1h" if "SET_4" in sid else ("1d" if "SET_2" in sid else "Unknown"))
    ltf_tf = "1h" if "SET_3" in sid else ("15m" if "SET_4" in sid else ("4h" if "SET_2" in sid else "Unknown"))
    
    time_to_mfe_hr = (mfe_ts - entry_ts) / 3600.0 if mfe_ts and entry_ts else 0.0
    time_mfe_to_exit_hr = (exit_ts - mfe_ts) / 3600.0 if exit_ts and mfe_ts else 0.0
    total_duration_hr = (exit_ts - entry_ts) / 3600.0 if exit_ts and entry_ts else 0.0
    
    # 2R protection simulation
    be_2r_price = entry_p + (2.0 * risk_dist) if is_long else entry_p - (2.0 * risk_dist)
    # Protection stop: entry + friction buffer (e.g. entry or entry + 0.10R)
    prot_stop_price = entry_p + 0.0012 * entry_p if is_long else entry_p - 0.0012 * entry_p
    
    print(f"\n--- Trade #{t.get('trade_id')} [{sid}] ---")
    print(f"Direction:               {direction} ({'LONG' if is_long else 'SHORT'})")
    print(f"MTF Timeframe:           {mtf_tf} (Confirmation swing required)")
    print(f"LTF Timeframe:           {ltf_tf} (Execution timeframe)")
    print(f"Entry Timestamp:         {entry_ts} ({ts_to_str(entry_ts)}) @ {entry_p:.4f}")
    print(f"Initial Stop Price:      {stop_p:.4f} (Risk Dist: {risk_dist:.4f} / {risk_dist/entry_p*100:.2f}%)")
    print(f"Target Price:            {target_p:.4f} (Planned RR: {t.get('raw_rr', 0):.2f}R)")
    print(f"MFE Reached:             +{mfe_r:.2f}R @ {meta.get('mfe_price', 0):.4f}")
    print(f"MFE Timestamp:           {mfe_ts} ({ts_to_str(mfe_ts)})")
    print(f"Time from Entry to MFE:  {time_to_mfe_hr:.2f} hours")
    print(f"Exit Timestamp:          {exit_ts} ({ts_to_str(exit_ts)}) @ {exit_p:.4f}")
    print(f"Time from MFE to Exit:   {time_mfe_to_exit_hr:.2f} hours")
    print(f"Total Trade Duration:    {total_duration_hr:.2f} hours")
    print(f"Final Exit Reason:       {exit_reason}")
    print(f"Final Stop Level:        {curr_stop:.4f} ({'Trailed' if abs(curr_stop - stop_p) > 1e-5 else 'Unchanged Initial Stop'})")
    print(f"Net Realized R:          {net_r:.2f}R (Dissipated: {mfe_r - net_r:.2f}R)")
    
    # Explain why MTF trailing failed
    if exit_reason == "INITIAL_LTF_SL":
        print(f"Trailing Diagnosis:      FAIL-TO-ADVANCE: Price reached +{mfe_r:.2f}R, but zero confirmed {mtf_tf} swing lows/highs formed before price crashed back to initial SL.")
    else:
        print(f"Trailing Diagnosis:      LATENCY LAG: MTF swing advanced stop to {curr_stop:.4f}, but confirmation required {time_mfe_to_exit_hr:.2f}h, locking only {net_r:.2f}R instead of securing profit.")
        
    print(f"Hypothetical +2R Impact: Protected stop at entry would have turned this {net_r:.2f}R loss into ~0.00R (Breakeven), saving +{abs(net_r):.2f}R of drawdown.")
