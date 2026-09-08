import json
import statistics

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

h0 = load_json('scratch/h0_dev_control_results.json')
a2 = load_json('scratch/anchor2_dev_results.json')
lock_1_0 = load_json('scratch/h_mgt_1_profit_lock_1_0_results.json')
lock_1_5 = load_json('scratch/h_mgt_1_profit_lock_1_5_results.json')

h0_trades = {(t['trade_id'], t['stream_id']): t for t in h0.get('trade_ledger', [])}
a2_trades = {(t['trade_id'], t['stream_id']): t for t in a2.get('trade_ledger', [])}
lock_1_0_trades = {(t['trade_id'], t['stream_id']): t for t in lock_1_0.get('trade_ledger', [])}
lock_1_5_trades = {(t['trade_id'], t['stream_id']): t for t in lock_1_5.get('trade_ledger', [])}

new_trades = {tid: t for tid, t in a2_trades.items() if tid not in h0_trades}

def print_metrics(trades_dict, label):
    trades = list(trades_dict.values())
    wins = [t for t in trades if t['net_r'] > 0]
    losses = [t for t in trades if t['net_r'] < 0]
    bes = [t for t in trades if t['net_r'] == 0]
    
    win_r = [t['net_r'] for t in wins]
    loss_r = [t['net_r'] for t in losses]
    all_r = [t['net_r'] for t in trades]
    
    print(f"\n--- {label} ---")
    print(f"N: {len(trades)}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}, BEs: {len(bes)}")
    print(f"Win Rate: {len(wins)/len(trades)*100:.1f}%" if trades else "Win Rate: N/A")
    print(f"Gross R: {sum(t['gross_r'] for t in trades):.2f}")
    print(f"Friction R: {sum(-t['fees_r'] - t['slippage_r'] for t in trades):.2f}")
    print(f"Net R: {sum(all_r):.2f}")
    print(f"Expectancy: {sum(all_r)/len(trades):.2f}" if trades else "Expectancy: N/A")
    gross_prof = sum(t['gross_r'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['gross_r'] for t in losses)) if losses else 0
    print(f"Profit Factor: {gross_prof/gross_loss:.2f}" if gross_loss > 0 else "Profit Factor: N/A")
    print(f"Average Winner: {statistics.mean(win_r):.2f}" if win_r else "Avg Win: N/A")
    print(f"Average Loser: {statistics.mean(loss_r):.2f}" if loss_r else "Avg Loss: N/A")
    print(f"Average MFE R: {statistics.mean([t['mfe_r'] for t in trades]):.2f}" if trades else "Avg MFE: N/A")
    print(f"Average MAE R: {statistics.mean([t['mae_r'] for t in trades]):.2f}" if trades else "Avg MAE: N/A")
    
    exits = {}
    for t in trades:
        exits[t['exit_reason']] = exits.get(t['exit_reason'], 0) + 1
    print(f"Exits: {exits}")
    
    provs = {}
    for t in trades:
        prov = t.get('metadata', {}).get('structural_provenance', {}).get('htf_target_provenance', 'UNKNOWN')
        provs[prov] = provs.get(prov, 0) + 1
    print(f"Provenance: {provs}")

print_metrics(h0_trades, "H0 CONTROL")
print_metrics(a2_trades, "ANCHOR_2 FULL")
print_metrics(lock_1_0_trades, "PROFIT LOCK +1.0R")
print_metrics(lock_1_5_trades, "PROFIT LOCK +1.5R")


