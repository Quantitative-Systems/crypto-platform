"""
Product 04 — Research Laboratory: Canonical BTC S3 Baseline Runner
Executes truthful historical baseline backtest on 50,000 1H candles for BTCUSDT S3 (1D -> 4H -> 1H).
Directly isolates Stream A (Fixed HTF TP + LTF SL) vs Stream B (HTF TP + MTF Structural Trailing).
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any

from market_data.warehouse_loader import WarehouseLoader
from market_intelligence.primitives import Candle
from research.replayer.causal_replayer import CausalReplayer
from risk_engine.contracts.risk_config import RiskConfig


def run_baseline():
    print("=" * 80)
    print("PROJECT TOP1 — CANONICAL STRATEGY HISTORICAL BASELINE")
    print("DATASET: BTCUSDT | SET_3 (1D -> 4H -> 1H) | 50,000 LTF CANDLES")
    print("MODE: RESEARCH (Unconstrained Candidate Population Measurement)")
    print("=" * 80)

    # 1. Load Data
    t0 = time.time()
    print("\n[1/4] Loading historical candle streams from warehouse cache...")
    htf_candles = WarehouseLoader.load_history("BTC/USDT", "1d", 50000)
    mtf_candles = WarehouseLoader.load_history("BTC/USDT", "4h", 50000)
    ltf_candles = WarehouseLoader.load_history("BTC/USDT", "1h", 50000)

    print(f"  -> HTF (1D): {len(htf_candles):,} candles ({datetime.fromtimestamp(htf_candles[0].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(htf_candles[-1].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')})")
    print(f"  -> MTF (4H): {len(mtf_candles):,} candles ({datetime.fromtimestamp(mtf_candles[0].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(mtf_candles[-1].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')})")
    print(f"  -> LTF (1H): {len(ltf_candles):,} candles ({datetime.fromtimestamp(ltf_candles[0].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')} to {datetime.fromtimestamp(ltf_candles[-1].timestamp, tz=timezone.utc).strftime('%Y-%m-%d')})")

    # Research Configuration: <=1% risk, >=4R floor, circuit breakers disabled for baseline measurement
    risk_config = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )

    # 2. Run Stream A: Fixed HTF Target + LTF SL (No Trailing)
    print("\n[2/4] Executing Stream A (Fixed HTF Target + LTF SL, No MTF Trailing)...")
    t_start_a = time.time()
    replayer_a = CausalReplayer(
        timeframe_set_id="SET_3",
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=False,
        cache_htf_mtf=True,
        risk_config=risk_config
    )
    result_a = replayer_a.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )
    t_dur_a = time.time() - t_start_a
    print(f"  -> Stream A completed in {t_dur_a:.2f}s | Closed Trades: {len(result_a['closed_trades'])}")

    # 3. Run Stream B: HTF Target + MTF Structural Trailing
    print("\n[3/4] Executing Stream B (Same Entries + HTF Target + MTF Structural Trailing)...")
    t_start_b = time.time()
    replayer_b = CausalReplayer(
        timeframe_set_id="SET_3",
        initial_balance=10000.0,
        maker_fee_rate=0.0000,
        taker_fee_rate=0.0005,
        slippage_bps=5.0,
        enable_mtf_trailing=True,
        cache_htf_mtf=True,
        risk_config=risk_config
    )
    result_b = replayer_b.run(
        symbol="BTCUSDT",
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )
    t_dur_b = time.time() - t_start_b
    print(f"  -> Stream B completed in {t_dur_b:.2f}s | Closed Trades: {len(result_b['closed_trades'])}")

    # 4. Forensic Analysis & Metric Computation
    print("\n[4/4] Computing full metric suite, trade provenance, and forensic distributions...")
    
    analytics_a = compute_stream_analytics(result_a, ltf_candles)
    analytics_b = compute_stream_analytics(result_b, ltf_candles)

    # Save to scratch results JSON
    os.makedirs("scratch", exist_ok=True)
    out_payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "symbol": "BTCUSDT",
            "timeframe_set": "SET_3 (1D -> 4H -> 1H)",
            "ltf_candles_count": len(ltf_candles),
            "start_date": datetime.fromtimestamp(ltf_candles[0].timestamp, tz=timezone.utc).isoformat(),
            "end_date": datetime.fromtimestamp(ltf_candles[-1].timestamp, tz=timezone.utc).isoformat(),
            "duration_days": round((ltf_candles[-1].timestamp - ltf_candles[0].timestamp) / 86400, 2)
        },
        "stream_a_fixed_tp": analytics_a,
        "stream_b_mtf_trailing": analytics_b
    }

    with open("scratch/canonical_btc_s3_baseline_results.json", "w") as f:
        json.dump(out_payload, f, indent=2)

    # Output Complete Formatted Report
    print_report(analytics_a, analytics_b, out_payload["dataset"])


def compute_stream_analytics(raw_result: Dict[str, Any], ltf_candles: List[Candle]) -> Dict[str, Any]:
    trades = raw_result.get("closed_trades", [])
    metrics = raw_result.get("metrics", {})
    
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0, "wins_count": 0, "losses_count": 0, "win_rate_pct": 0.0,
            "net_profit_usd": 0.0, "net_profit_pct": 0.0, "profit_factor": 0.0, "expectancy_r": 0.0,
            "cumulative_r": 0.0, "average_r": 0.0, "median_r": 0.0, "avg_win_r": 0.0, "avg_loss_r": 0.0,
            "max_drawdown_pct": 0.0, "max_drawdown_r": 0.0, "max_consecutive_losses": 0,
            "exit_attribution": {}, "hypothesis_breakdown": {}, "mfe_r_mean": 0.0, "mae_r_mean": 0.0,
            "setup_age_hours_mean": 0.0, "setup_age_hours_median": 0.0, "trade_duration_hours_mean": 0.0,
            "total_fees_usd": 0.0, "total_friction_usd": 0.0, "market_exposure_pct": 0.0, "trades_ledger": []
        }

    wins = [t for t in trades if (t.get("realized_pnl") or 0.0) > 0]
    losses = [t for t in trades if (t.get("realized_pnl") or 0.0) <= 0]
    
    win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0.0
    
    r_multiples = [t.get("realized_rr", 0.0) for t in trades]
    avg_r = sum(r_multiples) / total_trades if total_trades > 0 else 0.0
    sorted_r = sorted(r_multiples)
    median_r = sorted_r[len(sorted_r) // 2] if sorted_r else 0.0
    
    win_r = [t.get("realized_rr", 0.0) for t in wins]
    loss_r = [t.get("realized_rr", 0.0) for t in losses]
    avg_win_r = sum(win_r) / len(win_r) if win_r else 0.0
    avg_loss_r = sum(loss_r) / len(loss_r) if loss_r else 0.0
    
    expectancy_r = (len(wins)/total_trades * avg_win_r) + (len(losses)/total_trades * avg_loss_r) if total_trades > 0 else 0.0
    
    # Cumulative R & Max DD in R
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    curr_cons_losses = 0
    max_cons_losses = 0
    
    for r in r_multiples:
        cum_r += r
        if cum_r > peak_r:
            peak_r = cum_r
        dd_r = peak_r - cum_r
        if dd_r > max_dd_r:
            max_dd_r = dd_r
            
        if r <= 0:
            curr_cons_losses += 1
            if curr_cons_losses > max_cons_losses:
                max_cons_losses = curr_cons_losses
        else:
            curr_cons_losses = 0
            
    # Exit breakdown
    exit_counts: Dict[str, int] = {}
    exit_r_sums: Dict[str, float] = {}
    for t in trades:
        reason = t.get("exit_reason") or "UNKNOWN"
        exit_counts[reason] = exit_counts.get(reason, 0) + 1
        exit_r_sums[reason] = exit_r_sums.get(reason, 0.0) + (t.get("realized_rr") or 0.0)
        
    exit_breakdown = {}
    for reason, count in exit_counts.items():
        avg_r_exit = exit_r_sums[reason] / count if count > 0 else 0.0
        exit_breakdown[reason] = {
            "count": count,
            "pct": round((count / total_trades) * 100.0, 2),
            "avg_r": round(avg_r_exit, 3),
            "total_r": round(exit_r_sums[reason], 3)
        }



    # MAE, MFE, Setup Age, Duration, Fees
    mae_r_list = []
    mfe_r_list = []
    setup_age_hours_list = []
    trade_duration_hours_list = []
    total_fees_usd = 0.0
    total_friction_usd = 0.0
    
    trade_audit_ledger = []
    
    total_market_bars = len(ltf_candles)
    total_bars_in_position = 0
    
    for t in trades:
        dollar_risk = t.get("dollar_risk", 100.0) or 100.0
        fill_entry = t.get("fill_entry_price") or t.get("entry_price", 100.0)
        initial_sl = t.get("initial_stop_price") or 90.0
        stop_dist = abs(fill_entry - initial_sl) or 1.0
        is_long = t.get("directional_permission") == "PERMIT_LONG"
        
        meta = t.get("metadata", {})
        prov = meta.get("structural_provenance", {})
        
        # MFE / MAE
        mfe_price = meta.get("mfe_price", fill_entry)
        mae_price = meta.get("mae_price", fill_entry)
        
        if is_long:
            mfe_r = (mfe_price - fill_entry) / stop_dist
            mae_r = (fill_entry - mae_price) / stop_dist
        else:
            mfe_r = (fill_entry - mfe_price) / stop_dist
            mae_r = (mae_price - fill_entry) / stop_dist
            
        mfe_r_list.append(mfe_r)
        mae_r_list.append(mae_r)
        
        # Setup Age (from HTF context timestamp to entry timestamp)
        htf_ts = prov.get("htf_context_timestamp") or t.get("setup_timestamp") or 0
        entry_ts = t.get("entry_timestamp") or t.get("setup_timestamp") or 0
        exit_ts = t.get("exit_timestamp") or entry_ts
        
        setup_age_h = max(0.0, (entry_ts - htf_ts) / 3600.0) if htf_ts > 0 else 0.0
        trade_dur_h = max(0.0, (exit_ts - entry_ts) / 3600.0) if entry_ts > 0 else 0.0
        
        setup_age_hours_list.append(setup_age_h)
        trade_duration_hours_list.append(trade_dur_h)
        
        total_bars_in_position += int(trade_dur_h)
        total_fees_usd += (t.get("entry_fee", 0.0) + t.get("exit_fee", 0.0))
        total_friction_usd += t.get("total_friction_usd", 0.0)
        
        # Add enriched record to audit ledger
        trade_audit_ledger.append({
            "trade_id": t.get("trade_id"),
            "hypothesis_id": t.get("hypothesis_id"),
            "symbol": t.get("symbol"),
            "direction": t.get("directional_permission"),
            "setup_time": datetime.fromtimestamp(t.get("setup_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "entry_time": datetime.fromtimestamp(entry_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if entry_ts else "",
            "exit_time": datetime.fromtimestamp(exit_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if exit_ts else "",
            "duration_hours": round(trade_dur_h, 1),
            "setup_age_hours": round(setup_age_h, 1),
            "entry_price": round(fill_entry, 2),
            "initial_sl": round(initial_sl, 2),
            "final_sl": round(t.get("current_stop_price", initial_sl), 2),
            "target_price": round(t.get("target_price", 0.0), 2),
            "exit_price": round(t.get("exit_price", 0.0), 2),
            "exit_reason": t.get("exit_reason"),
            "planned_rr": round(t.get("raw_rr", 0.0), 2),
            "realized_rr": round(t.get("realized_rr", 0.0), 3),
            "realized_pnl_usd": round(t.get("realized_pnl", 0.0), 2),
            "dollar_risk": round(dollar_risk, 2),
            "position_units": round(t.get("position_units", 0.0), 4),
            "mfe_r": round(mfe_r, 2),
            "mae_r": round(mae_r, 2),
            "fees_usd": round(t.get("entry_fee", 0.0) + t.get("exit_fee", 0.0), 2),
            "provenance": {
                "htf_context_id": prov.get("htf_context_id"),
                "htf_macro_direction": prov.get("htf_macro_direction"),
                "htf_phase": prov.get("htf_phase"),
                "htf_expected_move": prov.get("htf_expected_move"),
                "htf_target_price": prov.get("htf_target_price"),
                "mtf_setup_id": prov.get("mtf_setup_id"),
                "mtf_setup_direction": prov.get("mtf_setup_direction"),
                "mtf_structural_event": prov.get("mtf_structural_event"),
                "mtf_keyzone_id": prov.get("mtf_keyzone_id"),
                "mtf_kz_creation_time": datetime.fromtimestamp(prov.get("mtf_kz_creation_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if prov.get("mtf_kz_creation_timestamp") else "",
                "mtf_retest_time": datetime.fromtimestamp(prov.get("mtf_retest_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if prov.get("mtf_retest_timestamp") else "",
                "ltf_confirmation_time": datetime.fromtimestamp(prov.get("ltf_confirmation_timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if prov.get("ltf_confirmation_timestamp") else "",
                "ltf_entry_reason": prov.get("ltf_entry_reason")
            }
        })

    exposure_pct = (total_bars_in_position / total_market_bars) * 100.0 if total_market_bars > 0 else 0.0

    return {
        "total_trades": total_trades,
        "wins_count": len(wins),
        "losses_count": len(losses),
        "win_rate_pct": round(win_rate, 2),
        "net_profit_usd": round(metrics.get("net_profit_usd", 0.0), 2),
        "net_profit_pct": round((metrics.get("net_profit_usd", 0.0) / 10000.0) * 100.0, 2),
        "profit_factor": round(metrics.get("profit_factor", 0.0), 3),
        "expectancy_r": round(expectancy_r, 3),
        "cumulative_r": round(cum_r, 3),
        "average_r": round(avg_r, 3),
        "median_r": round(median_r, 3),
        "avg_win_r": round(avg_win_r, 3),
        "avg_loss_r": round(avg_loss_r, 3),
        "max_drawdown_pct": round(metrics.get("max_drawdown_pct", 0.0) * 100.0, 2),
        "max_drawdown_r": round(max_dd_r, 2),
        "max_consecutive_losses": max_cons_losses,
        "exit_attribution": exit_breakdown,
        "mfe_r_mean": round(sum(mfe_r_list) / len(mfe_r_list), 2) if mfe_r_list else 0.0,
        "mae_r_mean": round(sum(mae_r_list) / len(mae_r_list), 2) if mae_r_list else 0.0,
        "setup_age_hours_mean": round(sum(setup_age_hours_list) / len(setup_age_hours_list), 1) if setup_age_hours_list else 0.0,
        "setup_age_hours_median": round(sorted(setup_age_hours_list)[len(setup_age_hours_list)//2], 1) if setup_age_hours_list else 0.0,
        "trade_duration_hours_mean": round(sum(trade_duration_hours_list) / len(trade_duration_hours_list), 1) if trade_duration_hours_list else 0.0,
        "total_fees_usd": round(total_fees_usd, 2),
        "total_friction_usd": round(total_friction_usd, 2),
        "market_exposure_pct": round(exposure_pct, 2),
        "trades_ledger": trade_audit_ledger
    }


def print_report(res_a: Dict[str, Any], res_b: Dict[str, Any], dataset: Dict[str, Any]):
    print("\n" + "=" * 80)
    print("CANONICAL HISTORICAL BASELINE RESULTS — RAW AUDIT REPORT")
    print("=" * 80)
    print(f"Asset:            {dataset['symbol']}")
    print(f"Timeframe Set:    {dataset['timeframe_set']}")
    print(f"Data Window:      {dataset['start_date']} -> {dataset['end_date']} ({dataset['duration_days']:.1f} days, {dataset['ltf_candles_count']:,} bars)")
    print(f"Risk Parameters:  Risk = 1.0% equity ($100 base) | Floor = >= 4.0R | Friction = 0.00% Maker, 0.05% Taker, 5.0 bps Slip")
    print("=" * 80)

    # 1. Comparison Table
    print("\n" + "-" * 80)
    print(f"{'METRIC':<32} | {'STREAM A (Fixed TP)':<20} | {'STREAM B (MTF Trailing)':<20}")
    print("-" * 80)
    
    rows = [
        ("Total Trades Closed", f"{res_a['total_trades']}", f"{res_b['total_trades']}"),
        ("Win Rate (%)", f"{res_a['win_rate_pct']:.2f}%", f"{res_b['win_rate_pct']:.2f}%"),
        ("Profit Factor", f"{res_a['profit_factor']:.3f}", f"{res_b['profit_factor']:.3f}"),
        ("Expectancy E[R]", f"{res_a['expectancy_r']:+.3f}R", f"{res_b['expectancy_r']:+.3f}R"),
        ("Cumulative R", f"{res_a['cumulative_r']:+.3f}R", f"{res_b['cumulative_r']:+.3f}R"),
        ("Net Profit ($)", f"${res_a['net_profit_usd']:+,.2f} ({res_a['net_profit_pct']:+.2f}%)", f"${res_b['net_profit_usd']:+,.2f} ({res_b['net_profit_pct']:+.2f}%)"),
        ("Average R / Trade", f"{res_a['average_r']:+.3f}R", f"{res_b['average_r']:+.3f}R"),
        ("Median R / Trade", f"{res_a['median_r']:+.3f}R", f"{res_b['median_r']:+.3f}R"),
        ("Average Winner", f"{res_a['avg_win_r']:+.3f}R", f"{res_b['avg_win_r']:+.3f}R"),
        ("Average Loser", f"{res_a['avg_loss_r']:+.3f}R", f"{res_b['avg_loss_r']:+.3f}R"),
        ("Max Drawdown (%)", f"{res_a['max_drawdown_pct']:.2f}%", f"{res_b['max_drawdown_pct']:.2f}%"),
        ("Max Drawdown (R)", f"{res_a['max_drawdown_r']:.2f}R", f"{res_b['max_drawdown_r']:.2f}R"),
        ("Max Consecutive Losses", f"{res_a['max_consecutive_losses']}", f"{res_b['max_consecutive_losses']}"),
        ("Mean MFE (Max Fav Excursion)", f"{res_a['mfe_r_mean']:.2f}R", f"{res_b['mfe_r_mean']:.2f}R"),
        ("Mean MAE (Max Adv Excursion)", f"{res_a['mae_r_mean']:.2f}R", f"{res_b['mae_r_mean']:.2f}R"),
        ("Mean Setup Age", f"{res_a['setup_age_hours_mean']:.1f} hrs ({res_a['setup_age_hours_mean']/24:.1f}d)", f"{res_b['setup_age_hours_mean']:.1f} hrs ({res_b['setup_age_hours_mean']/24:.1f}d)"),
        ("Median Setup Age", f"{res_a['setup_age_hours_median']:.1f} hrs", f"{res_b['setup_age_hours_median']:.1f} hrs"),
        ("Mean Trade Duration", f"{res_a['trade_duration_hours_mean']:.1f} hrs", f"{res_b['trade_duration_hours_mean']:.1f} hrs"),
        ("Total Fees & Friction ($)", f"${res_a['total_friction_usd']:.2f}", f"${res_b['total_friction_usd']:.2f}"),
        ("Market Exposure (%)", f"{res_a['market_exposure_pct']:.2f}%", f"{res_b['market_exposure_pct']:.2f}%")
    ]
    
    for label, val_a, val_b in rows:
        print(f"{label:<32} | {val_a:<20} | {val_b:<20}")
    print("-" * 80)

    # 2. Exit Reason Breakdown
    print("\n" + "=" * 80)
    print("EXIT REASON ATTRIBUTION")
    print("=" * 80)
    
    print("\n--- STREAM A: FIXED HTF TARGET (NO TRAIL) ---")
    for reason, data in res_a.get("exit_attribution", {}).items():
        print(f"  * {reason:<25}: {data['count']:>3} trades ({data['pct']:>5.1f}%) | Avg R: {data['avg_r']:>+6.3f}R | Total R: {data['total_r']:>+7.3f}R")

    print("\n--- STREAM B: WITH MTF STRUCTURAL TRAILING ---")
    for reason, data in res_b.get("exit_attribution", {}).items():
        print(f"  * {reason:<25}: {data['count']:>3} trades ({data['pct']:>5.1f}%) | Avg R: {data['avg_r']:>+6.3f}R | Total R: {data['total_r']:>+7.3f}R")



    # 4. Detailed Raw Trade Ledger
    print("\n" + "=" * 80)
    print("STREAM B RAW TRADE AUDIT LEDGER (COMPLETE PROVENANCE)")
    print("=" * 80)
    ledger = res_b.get("trades_ledger", [])
    if not ledger:
        print("  [No trades executed]")
    else:
        for idx, t in enumerate(ledger, 1):
            prov = t.get("provenance", {})
            print(f"\n[{idx:02d}] TRADE {t['trade_id'][:8]} | {t['hypothesis_id']} | {t['direction']}")
            print(f"     Setup: {t['setup_time']} | Entry: {t['entry_time']} | Exit: {t['exit_time']} (Dur: {t['duration_hours']}h, Age: {t['setup_age_hours']}h)")
            print(f"     Entry: ${t['entry_price']:,.2f} | Init SL: ${t['initial_sl']:,.2f} | Final SL: ${t['final_sl']:,.2f} | TP: ${t['target_price']:,.2f}")
            print(f"     Exit:  ${t['exit_price']:,.2f} via {t['exit_reason']} | Realized: {t['realized_rr']:+.3f}R (${t['realized_pnl_usd']:+,.2f}) | MFE: {t['mfe_r']:+.2f}R | MAE: {t['mae_r']:+.2f}R")
            print(f"     Provenance: HTF Context [{prov.get('htf_context_id')}] Dir={prov.get('htf_macro_direction')} Phase={prov.get('htf_phase')} Move={prov.get('htf_expected_move')} Target=${prov.get('htf_target_price', 0):,.2f}")
            print(f"                 MTF Setup [{prov.get('mtf_setup_id')}] Event={prov.get('mtf_structural_event')} KZ=[{prov.get('mtf_keyzone_id')}] Retest={prov.get('mtf_retest_time')}")
            print(f"                 LTF Trigger Confirmed={prov.get('ltf_confirmation_time')} Reason={prov.get('ltf_entry_reason')}")

    print("\n" + "=" * 80)
    print("END OF CANONICAL HISTORICAL BASELINE REPORT")
    print("=" * 80)


if __name__ == "__main__":
    run_baseline()
