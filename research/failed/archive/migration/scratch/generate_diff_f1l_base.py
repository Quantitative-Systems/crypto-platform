import json

with open('scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json') as f:
    base_data = json.load(f)

with open('scratch/exp_f1l_tgt_struct_milestone_01_dev_results.json') as f:
    f1l_data = json.load(f)

base_trades = base_data['all_trades']
f1l_trades = f1l_data['all_trades']

print(f"Total base trades: {len(base_trades)} | Total f1l trades: {len(f1l_trades)}")

diff_rows = []

for i in range(len(base_trades)):
    bt = base_trades[i]
    ft = f1l_trades[i]
    
    stream = bt.get('stream_id')
    entry_p = bt.get('entry_price')
    stop_p = bt.get('initial_stop_price')
    target_p = bt.get('target_price')
    mfe = bt.get('mfe_r')
    mae = bt.get('mae_r')
    
    base_exit_p = bt.get('exit_price')
    base_reason = bt.get('exit_reason')
    base_r = float(bt.get('realized_r', bt.get('realized_rr', 0.0)))
    
    f1l_exit_p = ft.get('exit_price')
    f1l_reason = ft.get('exit_reason')
    f1l_r = float(ft.get('realized_r', ft.get('realized_rr', 0.0)))
    
    diff_r = f1l_r - base_r
    
    diff_rows.append({
        "trade_idx": i + 1,
        "stream": stream,
        "entry": entry_p,
        "stop": stop_p,
        "target": target_p,
        "mfe": mfe,
        "mae": mae,
        "base_exit_price": base_exit_p,
        "base_reason": base_reason,
        "base_r": base_r,
        "milestone_exit_price": f1l_exit_p,
        "milestone_reason": f1l_reason,
        "milestone_r": f1l_r,
        "diff_r": diff_r
    })

for row in diff_rows:
    print(f"Trade {row['trade_idx']:2d} ({row['stream']}):")
    print(f"  Entry: {row['entry']} | Stop: {row['stop']} | Target: {row['target']} | MFE: {row['mfe']:.4f}R | MAE: {row['mae']:.4f}R")
    print(f"  Base Exit: {row['base_exit_price']} ({row['base_reason']}) -> Realized: {row['base_r']:+.4f}R")
    print(f"  F1L  Exit: {row['milestone_exit_price']} ({row['milestone_reason']}) -> Realized: {row['milestone_r']:+.4f}R")
    print(f"  Delta Realized R: {row['diff_r']:+.4f}R\n")

with open('scratch/trade_by_trade_diff_f1l_vs_base.json', 'w') as f:
    json.dump(diff_rows, f, indent=2)
print("Saved to scratch/trade_by_trade_diff_f1l_vs_base.json")
