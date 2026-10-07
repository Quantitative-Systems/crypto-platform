"""
Product 04 — Research Laboratory: Full Institutional 12-Stream Matrix Backtest
Executes all 4 Timeframe Sets across all 3 Assets (BTC, ETH, SOL) with the complete
institutional production stack: Dual MTF Structural Trailing, +1.0R Profit-Lock Ratchet,
Alpha Regime Gating, and real Binance friction.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
import numpy as np
from typing import Dict, Any, List

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from risk_engine.contracts.risk_config import RiskConfig


ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4"]

TF_SET_LABELS = {
    "SET_1": "SET_1_INVESTING (1M -> 1W -> 1D)",
    "SET_2": "SET_2_POSITIONAL (1W -> 1D -> 4H)",
    "SET_3": "SET_3_SWING (1D -> 4H -> 1H)",
    "SET_4": "SET_4_INTRADAY (4H -> 1H -> 15M)"
}


def compute_metrics(trades: List[Dict[str, Any]], initial_equity: float = 10000.0) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
            "total_realized_r": 0.0, "expectancy_r": 0.0, "median_r": 0.0,
            "avg_win_r": 0.0, "avg_loss_r": 0.0, "max_drawdown_usd": 0.0, "max_drawdown_pct": 0.0,
            "longest_win_streak": 0, "longest_loss_streak": 0,
            "avg_duration_hours": 0.0, "long_trades": 0, "short_trades": 0,
            "exit_attribution": {}, "exit_percentages": {}, "exit_avg_r": {}
        }

    wins = [t for t in trades if t.get("net_pnl", 0.0) > 0]
    losses = [t for t in trades if t.get("net_pnl", 0.0) <= 0]
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / n * 100.0)

    gp = sum(t.get("net_pnl", 0.0) for t in wins)
    gl = abs(sum(t.get("net_pnl", 0.0) for t in losses))
    pf = (gp / gl) if gl > 0 else (gp if gp > 0 else 0.0)
    net_pnl = sum(t.get("net_pnl", 0.0) for t in trades)

    r_list = [t.get("net_r", 0.0) for t in trades]
    total_r = sum(r_list)
    exp_r = float(np.mean(r_list))
    med_r = float(np.median(r_list))
    avg_win_r = float(np.mean([t.get("net_r", 0.0) for t in wins])) if w_count > 0 else 0.0
    avg_loss_r = float(np.mean([t.get("net_r", 0.0) for t in losses])) if l_count > 0 else 0.0

    # Drawdown
    cum_pnl = np.cumsum([t.get("net_pnl", 0.0) for t in trades])
    peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else np.array([0.0])
    dd_usd = peak - cum_pnl
    max_dd_usd = float(np.max(dd_usd)) if len(dd_usd) > 0 else 0.0
    running_eq = initial_equity + cum_pnl
    eq_peak = np.maximum.accumulate(running_eq) if len(running_eq) > 0 else np.array([initial_equity])
    dd_pct = (eq_peak - running_eq) / eq_peak * 100.0 if len(running_eq) > 0 else np.array([0.0])
    max_dd_pct = float(np.max(dd_pct)) if len(dd_pct) > 0 else 0.0

    # Streaks
    cur_w, max_w = 0, 0
    cur_l, max_l = 0, 0
    for t in trades:
        if t.get("net_pnl", 0.0) > 0:
            cur_w += 1
            cur_l = 0
            if cur_w > max_w: max_w = cur_w
        else:
            cur_l += 1
            cur_w = 0
            if cur_l > max_l: max_l = cur_l

    # Durations
    durations = []
    for t in trades:
        e_ts = t.get("entry_timestamp") or t.get("setup_timestamp", 0)
        x_ts = t.get("exit_timestamp") or e_ts
        if x_ts and e_ts and x_ts >= e_ts:
            durations.append((x_ts - e_ts) / 3600.0)
    avg_dur = float(np.mean(durations)) if durations else 0.0

    # Exit attribution
    exit_counts = {}
    exit_r_lists = {}
    for t in trades:
        reason = t.get("exit_reason", "UNKNOWN")
        r_val = t.get("net_r", 0.0)
        exit_counts[reason] = exit_counts.get(reason, 0) + 1
        if reason not in exit_r_lists:
            exit_r_lists[reason] = []
        exit_r_lists[reason].append(r_val)

    exit_pcts = {k: (v / n * 100.0) for k, v in exit_counts.items()}
    exit_avg_r = {k: float(np.mean(v)) for k, v in exit_r_lists.items()}

    longs = len([t for t in trades if t.get("directional_permission") == "PERMIT_LONG"])
    shorts = len([t for t in trades if t.get("directional_permission") == "PERMIT_SHORT"])

    return {
        "total_trades": n,
        "wins": w_count,
        "losses": l_count,
        "win_rate_pct": wr,
        "gross_profit": gp,
        "gross_loss": gl,
        "profit_factor": pf,
        "net_pnl": net_pnl,
        "total_realized_r": total_r,
        "expectancy_r": exp_r,
        "median_r": med_r,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "longest_win_streak": max_w,
        "longest_loss_streak": max_l,
        "avg_duration_hours": avg_dur,
        "long_trades": longs,
        "short_trades": shorts,
        "exit_attribution": exit_counts,
        "exit_percentages": exit_pcts,
        "exit_avg_r": exit_avg_r
    }


def run_full_matrix(enable_regime_filter: bool = True) -> List[Dict[str, Any]]:
    print("==========================================================================================================")
    print("      PRODUCT 04 — RESEARCH LABORATORY: INSTITUTIONAL 12-STREAM MATRIX BACKTEST")
    print(f"      (Regime Filter: {'ENABLED' if enable_regime_filter else 'DISABLED'} | Profit-Lock: +1.0R -> +0.25R)")
    print("==========================================================================================================\n")

    matrix_results = []
    
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            symbol = f"{asset}USDT"
            tf_set = TimeframeAligner.get_set(tf_set_id)
            
            htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=50000)
            mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=50000)
            ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=50000)
            
            research_risk_cfg = RiskConfig(
                enable_circuit_breakers=False,
                max_risk_fraction=0.01,
                min_rr_floor=4.0
            )
            
            replayer = CausalReplayer(
                timeframe_set_id=tf_set_id,
                initial_balance=10000.0,
                maker_fee_rate=0.0000,
                taker_fee_rate=0.0005,
                slippage_bps=5.0,
                enable_mtf_trailing=True,
                enable_profit_lock=True,
                lockin_r=1.0,
                giveback_r=0.75,
                enable_regime_filter=enable_regime_filter,
                cache_htf_mtf=True,
                risk_config=research_risk_cfg
            )
            
            t0 = time.time()
            res = replayer.run(
                symbol=symbol,
                htf_candles=htf_candles,
                mtf_candles=mtf_candles,
                ltf_candles=ltf_candles
            )
            elapsed = time.time() - t0
            
            closed_trades = res["closed_trades"]
            m = compute_metrics(closed_trades)
            
            hyp_a_trades = [t for t in closed_trades if "PULLBACK" in str(t.get("hypothesis_id", "")) or "PULLBACK" in str(t.get("metadata", {}).get("strategy_type", ""))]
            hyp_b_trades = [t for t in closed_trades if "CONTINUATION" in str(t.get("hypothesis_id", "")) or "CONTINUATION" in str(t.get("metadata", {}).get("strategy_type", ""))]
            
            ma = compute_metrics(hyp_a_trades)
            mb = compute_metrics(hyp_b_trades)
            
            stream_record = {
                "symbol": symbol,
                "tf_set_id": tf_set_id,
                "tf_set_label": TF_SET_LABELS[tf_set_id],
                "candles_processed": len(ltf_candles),
                "execution_time_sec": elapsed,
                "combined": m,
                "strategy_a": ma,
                "strategy_b": mb
            }
            matrix_results.append(stream_record)
            print(f"  • [{symbol:<7} | {tf_set_id:<5}] Done in {elapsed:5.1f}s | Trades: {m['total_trades']:4d} | WR: {m['win_rate_pct']:5.1f}% | PF: {m['profit_factor']:5.2f} | Net PnL: ${m['net_pnl']:+10,.2f} | Total R: {m['total_realized_r']:+7.1f}R")

    return matrix_results


def print_matrix_summary(results: List[Dict[str, Any]]) -> None:
    print("\n" + "=" * 135)
    print("                                     FULL 12-STREAM MATRIX PERFORMANCE SUMMARY")
    print("=" * 135)
    header = f"{'Stream (Asset / Timeframe Set)':<36} | {'Trd':<4} | {'WR%':<5} | {'PF':<5} | {'Exp E[R]':<8} | {'Net R':<8} | {'Net PnL ($)':<12} | {'Max DD%':<7} | {'Strk(W/L)':<9} | {'Dur(h)':<6}"
    print(header)
    print("-" * 135)

    tot_trades = 0
    tot_wins = 0
    tot_pnl = 0.0
    tot_r = 0.0
    tot_gp = 0.0
    tot_gl = 0.0

    for s in results:
        sym = s["symbol"]
        set_id = s["tf_set_id"]
        m = s["combined"]
        
        tot_trades += m["total_trades"]
        tot_wins += m["wins"]
        tot_pnl += m["net_pnl"]
        tot_r += m["total_realized_r"]
        tot_gp += m["gross_profit"]
        tot_gl += m["gross_loss"]
        
        strk = f"{m['longest_win_streak']}/{m['longest_loss_streak']}"
        label = f"{sym} | {TF_SET_LABELS[set_id].split(' ')[0]}"
        print(f"{label:<36} | {m['total_trades']:<4} | {m['win_rate_pct']:<5.1f} | {m['profit_factor']:<5.2f} | {m['expectancy_r']:<+8.2f} | {m['total_realized_r']:<+8.1f} | ${m['net_pnl']:<11,.2f} | {m['max_drawdown_pct']:<6.1f}% | {strk:<9} | {m['avg_duration_hours']:<6.1f}")

    print("-" * 135)
    overall_wr = (tot_wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
    overall_pf = (tot_gp / tot_gl) if tot_gl > 0 else 0.0
    overall_exp = (tot_r / tot_trades) if tot_trades > 0 else 0.0
    print(f"{'PORTFOLIO TOTAL / AGGREGATE':<36} | {tot_trades:<4} | {overall_wr:<5.1f} | {overall_pf:<5.2f} | {overall_exp:<+8.2f} | {tot_r:<+8.1f} | ${tot_pnl:<11,.2f} | -       | -         | -")
    print("=" * 135)

    # Timeframe Set Breakdown
    print("\n" + "=" * 135)
    print("                                      TIMEFRAME SET HORIZON BREAKDOWN")
    print("=" * 135)
    for tf_set_id in TF_SETS:
        sub = [s["combined"] for s in results if s["tf_set_id"] == tf_set_id]
        t = sum(x["total_trades"] for x in sub)
        w = sum(x["wins"] for x in sub)
        gp = sum(x["gross_profit"] for x in sub)
        gl = sum(x["gross_loss"] for x in sub)
        pnl = sum(x["net_pnl"] for x in sub)
        r = sum(x["total_realized_r"] for x in sub)
        wr = (w / t * 100.0) if t > 0 else 0.0
        pf = (gp / gl) if gl > 0 else 0.0
        exp_r = (r / t) if t > 0 else 0.0
        print(f"  • {TF_SET_LABELS[tf_set_id]:<38} | Trades: {t:4d} | WR: {wr:5.1f}% | PF: {pf:5.2f} | Net PnL: ${pnl:+11,.2f} | Total R: {r:+8.1f}R | Exp E[R]: {exp_r:+5.2f}R")
    print("=" * 135 + "\n")


if __name__ == "__main__":
    results = run_full_matrix(enable_regime_filter=True)
    print_matrix_summary(results)
    
    # Save results artifact
    out_dir = os.path.join(ROOT_DIR, "research", "results")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "INSTITUTIONAL_12_STREAM_MATRIX.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved complete institutional backtest results to: {out_file}")
