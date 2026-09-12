import json
import os
from collections import defaultdict
from datetime import datetime

with open('scratch/canonical_h_mom_01_dev_results.json') as f:
    data = json.load(f)

trades = data['all_trades']
stream_results = data['stream_results']
agg = data['aggregate_performance']

print("=" * 80)
print("H-MOM-01 DETAILED FORENSIC ATTRIBUTION REPORT")
print("=" * 80)

print(f"Total Streams Analyzed: {len(stream_results)}")
print(f"Total Executed Trades: {len(trades)}")

# 1. Funnel
total_candidates = sum(len(s.get('all_candidates', [])) for s in stream_results)
total_htf_qualified = 0
total_mtf_aligned = 0
total_mtf_retested = 0
total_ltf_triggered = 0
total_risk_gated = 0
total_entered = 0

for s in stream_results:
    for c in s.get('all_candidates', []):
        stages = c.get('stages_reached', [])
        if "HTF_QUALIFIED" in stages:
            total_htf_qualified += 1
        if "WAIT_MTF_ALIGNMENT" in stages:
            total_mtf_aligned += 1
        if "WAIT_MTF_RETEST" in stages:
            total_mtf_retested += 1
        if "WAIT_LTF_TRIGGER" in stages:
            total_ltf_triggered += 1
        if "RISK_GATE" in stages:
            total_risk_gated += 1
        if "ENTERED" in stages:
            total_entered += 1

print("\n--- CANDIDATE FUNNEL ---")
print(f"Total Candidates Spawned: {total_candidates}")
print(f"HTF Qualified:            {total_htf_qualified}")
print(f"MTF Alignment Reached:    {total_mtf_aligned}")
print(f"MTF Retest Reached:       {total_mtf_retested}")
print(f"LTF Trigger Reached:      {total_ltf_triggered}")
print(f"Risk Gate Reached:        {total_risk_gated}")
print(f"Orders Entered:           {total_entered}")
print(f"Execution Fill Rate:      {len(trades) / max(total_entered, 1) * 100:.1f}%")

# 2. Performance Metrics
wins = [t for t in trades if t['net_r'] > 0]
losses = [t for t in trades if t['net_r'] <= 0]
win_rate = len(wins) / len(trades) * 100 if trades else 0.0
avg_win = sum(t['net_r'] for t in wins) / len(wins) if wins else 0.0
avg_loss = sum(t['net_r'] for t in losses) / len(losses) if losses else 0.0
gross_wins = sum(t['net_r'] for t in wins)
gross_losses = abs(sum(t['net_r'] for t in losses))
pf = gross_wins / gross_losses if gross_losses > 0 else 0.0
net_r = sum(t['net_r'] for t in trades)
expectancy = net_r / len(trades) if trades else 0.0
total_friction_r = sum(t['fees_r'] + t['slippage_r'] + t['funding_r'] for t in trades)

# Target reachability
target_hits = [t for t in trades if t.get('exit_reason') == 'TARGET_HIT' or 'TARGET' in t.get('exit_reason', '')]
reachability = len(target_hits) / len(trades) * 100 if trades else 0.0

print("\n--- SUMMARY METRICS ---")
print(f"Trades (N):           {len(trades)}")
print(f"Wins / Losses:        {len(wins)} / {len(losses)}")
print(f"Win Rate:             {win_rate:.2f}%")
print(f"Average Win:          {avg_win:+.4f}R")
print(f"Average Loss:         {avg_loss:+.4f}R")
print(f"Expectancy:           {expectancy:+.4f}R")
print(f"Profit Factor:        {pf:.4f}")
print(f"Net Realized R:       {net_r:+.4f}R")
print(f"Gross R:              {agg.get('gross_r', 0.0):+.4f}R")
print(f"Friction Drag:        {total_friction_r:.4f}R ({total_friction_r / len(trades):.4f}R/trade)")
print(f"Max Drawdown:         {agg.get('max_drawdown_r', 0.0):.4f}R")
print(f"Target Reachability:  {reachability:.1f}% ({len(target_hits)}/{len(trades)})")
print(f"Avg / Med MFE:        {agg.get('avg_mfe_r', 0.0):.4f}R / {agg.get('median_mfe_r', 0.0):.4f}R")
print(f"Avg / Med MAE:        {agg.get('avg_mae_r', 0.0):.4f}R / {agg.get('median_mae_r', 0.0):.4f}R")

# 3. Asset Breakdown
print("\n--- PERFORMANCE BY ASSET ---")
by_asset = defaultdict(list)
for t in trades:
    asset = t['symbol'].split('/')[0]
    by_asset[asset].append(t)

for asset in ["BTC", "ETH", "SOL"]:
    a_trades = by_asset[asset]
    a_wins = [t for t in a_trades if t['net_r'] > 0]
    a_losses = [t for t in a_trades if t['net_r'] <= 0]
    a_net_r = sum(t['net_r'] for t in a_trades)
    a_exp = a_net_r / len(a_trades) if a_trades else 0.0
    a_gw = sum(t['net_r'] for t in a_wins)
    a_gl = abs(sum(t['net_r'] for t in a_losses))
    a_pf = a_gw / a_gl if a_gl > 0 else (999.0 if a_gw > 0 else 0.0)
    print(f"Asset {asset:4s} | N: {len(a_trades):2d} | W/L: {len(a_wins):2d}/{len(a_losses):2d} | WR: {len(a_wins)/max(len(a_trades),1)*100:5.1f}% | Net R: {a_net_r:+7.4f}R | E[R]: {a_exp:+6.4f}R | PF: {a_pf:5.2f}")

# 4. Set Breakdown
print("\n--- PERFORMANCE BY TIMEFRAME SET ---")
by_set = defaultdict(list)
for t in trades:
    tf_set = t['timeframe_set']
    by_set[tf_set].append(t)

for tf_set in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
    s_trades = by_set[tf_set]
    s_wins = [t for t in s_trades if t['net_r'] > 0]
    s_losses = [t for t in s_trades if t['net_r'] <= 0]
    s_net_r = sum(t['net_r'] for t in s_trades)
    s_exp = s_net_r / len(s_trades) if s_trades else 0.0
    s_gw = sum(t['net_r'] for t in s_wins)
    s_gl = abs(sum(t['net_r'] for t in s_losses))
    s_pf = s_gw / s_gl if s_gl > 0 else (999.0 if s_gw > 0 else 0.0)
    print(f"Set {tf_set:5s} | N: {len(s_trades):2d} | W/L: {len(s_wins):2d}/{len(s_losses):2d} | WR: {len(s_wins)/max(len(s_trades),1)*100:5.1f}% | Net R: {s_net_r:+7.4f}R | E[R]: {s_exp:+6.4f}R | PF: {s_pf:5.2f}")

# 5. Year / Regime Breakdown
print("\n--- PERFORMANCE BY YEAR ---")
by_year = defaultdict(list)
for t in trades:
    ts = t.get('entry_timestamp') or t.get('setup_timestamp') or 0
    dt = datetime.utcfromtimestamp(ts)
    by_year[dt.year].append(t)

for yr in sorted(by_year.keys()):
    y_trades = by_year[yr]
    y_wins = [t for t in y_trades if t['net_r'] > 0]
    y_net_r = sum(t['net_r'] for t in y_trades)
    y_exp = y_net_r / len(y_trades) if y_trades else 0.0
    print(f"Year {yr} | N: {len(y_trades):2d} | W/L: {len(y_wins):2d}/{len(y_trades)-len(y_wins):2d} | Net R: {y_net_r:+7.4f}R | E[R]: {y_exp:+6.4f}R")

# 6. Exit Reason Breakdown
print("\n--- EXIT REASONS ---")
by_exit = defaultdict(list)
for t in trades:
    by_exit[t.get('exit_reason', 'UNKNOWN')].append(t)

for ex, ex_trades in by_exit.items():
    ex_net_r = sum(t['net_r'] for t in ex_trades)
    print(f"Exit Reason: {ex:<30s} | N: {len(ex_trades):2d} | Net R: {ex_net_r:+7.4f}R")

# 7. Trade-by-trade list
print("\n--- TRADE-BY-TRADE LEDGER ---")
print(f"{'#':<3} | {'Stream':<10} | {'Dir':<5} | {'Entry Date':<19} | {'Entry':<10} | {'Stop':<10} | {'Target':<10} | {'Exit Price':<10} | {'Exit Reason':<25} | {'Net R':<8} | {'MFE R':<7}")
for idx, t in enumerate(trades, 1):
    ts = t.get('entry_timestamp', 0)
    dt_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "N/A"
    print(f"{idx:<3} | {t.get('stream_id',''):<10} | {t.get('direction',''):<5} | {dt_str:<19} | {t.get('fill_entry_price',0.0):<10.2f} | {t.get('initial_stop_price',0.0):<10.2f} | {t.get('target_price',0.0):<10.2f} | {t.get('exit_price',0.0):<10.2f} | {t.get('exit_reason',''):<25} | {t.get('net_r',0.0):+7.4f} | {t.get('mfe_r',0.0):5.2f}")
