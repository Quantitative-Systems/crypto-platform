"""
Parser and formatter for Gate 5 OOS validation report.
"""

import json

with open("/home/mrcn2/crypto-platform/scratch/gate5_oos_validation_results.json", "r") as f:
    data = json.load(f)

print("=" * 120)
print("GATE 5 OUT-OF-SAMPLE VALIDATION & INTEGRITY AUDIT REPORT")
print("=" * 120)

for s in data:
    sym = s["symbol"]
    set_id = s["tf_set_id"]
    status = s["status"]
    
    is_comb = s["is_stats"]["combined"]
    oos_comb = s["oos_stats"]["combined"]
    
    is_a = s["is_stats"]["strategy_a"]
    oos_a = s["oos_stats"]["strategy_a"]
    
    is_b = s["is_stats"]["strategy_b"]
    oos_b = s["oos_stats"]["strategy_b"]
    
    ret = s["retention"]
    life = s["setup_lifecycle"]
    
    print(f"\n{'#' * 80}")
    print(f"STREAM: {sym} | {set_id} | STATUS: [{status}]")
    print(f"Candles: {s['total_candles']} (IS: {s['is_candles']} | OOS: {s['oos_candles']})")
    print(f"Date Range: {s['start_dt']}  -->  Split: {s['split_dt']}  -->  End: {s['end_dt']}")
    print(f"{'#' * 80}")
    
    print("\n--- 1. OVERALL IN-SAMPLE (IS) vs OUT-OF-SAMPLE (OOS) ---")
    print(f"{'Metric':<25} | {'In-Sample (IS: 70%)':<22} | {'Out-Of-Sample (OOS: 30%)':<24} | {'Retention / Decay':<18}")
    print("-" * 95)
    print(f"{'Trades':<25} | {is_comb['total_trades']:<22} | {oos_comb['total_trades']:<24} | {oos_comb['total_trades']/(is_comb['total_trades'] or 1):.2f}x")
    print(f"{'Win Rate':<25} | {is_comb['win_rate_pct']:<21.2f}% | {oos_comb['win_rate_pct']:<23.2f}% | {ret['wr_retention']:.2f}x")
    print(f"{'Profit Factor':<25} | {is_comb['profit_factor']:<22.2f} | {oos_comb['profit_factor']:<24.2f} | {ret['pf_retention']:.2f}x")
    print(f"{'Expectancy E[R]':<25} | {is_comb['expectancy_r']:<+21.2f}R | {oos_comb['expectancy_r']:<+23.2f}R | {ret['exp_retention']:.2f}x")
    print(f"{'Total Realized R':<25} | {is_comb['total_realized_r']:<+21.2f}R | {oos_comb['total_realized_r']:<+23.2f}R | -")
    print(f"{'Net PnL ($)':<25} | ${is_comb['net_pnl']:<21,.2f} | ${oos_comb['net_pnl']:<23,.2f} | -")
    print(f"{'Median R':<25} | {is_comb['median_r']:<+21.2f}R | {oos_comb['median_r']:<+23.2f}R | -")
    print(f"{'Avg Winner / Loser':<25} | {is_comb['avg_win_r']:+.2f}R / {is_comb['avg_loss_r']:+.2f}R{' ':5} | {oos_comb['avg_win_r']:+.2f}R / {oos_comb['avg_loss_r']:+.2f}R{' ':7} | -")
    print(f"{'Longs / Shorts':<25} | {is_comb['long_trades']} L / {is_comb['short_trades']} S{' ':10} | {oos_comb['long_trades']} L / {oos_comb['short_trades']} S{' ':12} | -")
    print(f"{'Max Drawdown ($)':<25} | ${is_comb['max_drawdown_usd']:<21,.2f} | ${oos_comb['max_drawdown_usd']:<23,.2f} | -")
    
    print("\n--- 2. STRATEGY BREAKDOWN (OOS ONLY) ---")
    print(f"  Strategy A (PULLBACK_RIDING):     Trades: {oos_a['total_trades']:3d} | WR: {oos_a['win_rate_pct']:5.2f}% | PF: {oos_a['profit_factor']:5.2f} | E[R]: {oos_a['expectancy_r']:+5.2f}R | Realized R: {oos_a['total_realized_r']:+7.2f}R")
    print(f"  Strategy B (CONTINUATION_RIDING): Trades: {oos_b['total_trades']:3d} | WR: {oos_b['win_rate_pct']:5.2f}% | PF: {oos_b['profit_factor']:5.2f} | E[R]: {oos_b['expectancy_r']:+5.2f}R | Realized R: {oos_b['total_realized_r']:+7.2f}R")

    print("\n--- 3. EXIT ATTRIBUTION (OOS ONLY) ---")
    print(f"{'Exit Class':<25} | {'Count':<8} | {'Frequency (%)':<15} | {'Avg Realized R':<15}")
    print("-" * 70)
    for exit_k, count in oos_comb["exit_attribution"].items():
        freq = count / (oos_comb["total_trades"] or 1) * 100.0
        avg_r = oos_comb["exit_avg_r"].get(exit_k, 0.0)
        print(f"{exit_k:<25} | {count:<8} | {freq:<14.1f}% | {avg_r:+14.2f}R")
        
    print(f"\n--- 4. LIFECYCLE AUDIT ---")
    print(f"  Mean Setup Age: {life['mean_setup_age_hours']:.1f} hours | Max Setup Age: {life['max_setup_age_hours']:.1f} hours")
