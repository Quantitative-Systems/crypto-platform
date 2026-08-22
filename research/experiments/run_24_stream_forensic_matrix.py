"""
Product 04 — Research Laboratory: Gate 5B Full 24-Stream Strategy Forensic Matrix & Ablation Suite
Executes the Frozen Canonical 3-Timeframe State Machine across:
  - 3 Assets: BTCUSDT, ETHUSDT, SOLUSDT
  - 4 Timeframe Sets:
      SET_1_INVESTING:  1M -> 1W -> 1D
      SET_2_POSITIONAL: 1W -> 1D -> 4H
      SET_3_SWING:      1D -> 4H -> 1H
      SET_4_INTRADAY:   4H -> 1H -> 15M
      UNIFIED_STRATEGY
Total = 12 Strategy Streams + Controlled Ablations + Regime Forensics.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
import numpy as np
from typing import Dict, Any, List, Optional

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


def compute_stream_metrics(trades: List[Dict[str, Any]], initial_equity: float = 10000.0) -> Dict[str, Any]:
    t_count = len(trades)
    if t_count == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
            "total_realized_r": 0.0, "expectancy_r": 0.0, "median_r": 0.0,
            "avg_win_r": 0.0, "avg_loss_r": 0.0, "max_drawdown_usd": 0.0, "max_drawdown_pct": 0.0,
            "longest_win_streak": 0, "longest_loss_streak": 0,
            "avg_duration_hours": 0.0, "median_duration_hours": 0.0,
            "avg_mfe_r": 0.0, "avg_mae_r": 0.0, "mfe_to_realized_conversion": 0.0,
            "long_trades": 0, "short_trades": 0,
            "exit_attribution": {}, "exit_percentages": {}, "exit_avg_r": {},
            "regime_breakdown": {}
        }
        
    wins = [t for t in trades if t.get("net_pnl", 0.0) > 0]
    losses = [t for t in trades if t.get("net_pnl", 0.0) <= 0]
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / t_count * 100.0)
    
    gp = sum(t.get("net_pnl", 0.0) for t in wins)
    gl = abs(sum(t.get("net_pnl", 0.0) for t in losses))
    pf = (gp / gl) if gl > 0 else (gp if gp > 0 else 0.0)
    net_pnl = sum(t.get("net_pnl", 0.0) for t in trades)
    
    r_multiples = [t.get("net_r", 0.0) for t in trades]
    total_r = sum(r_multiples)
    exp_r = float(np.mean(r_multiples))
    med_r = float(np.median(r_multiples))
    avg_win_r = float(np.mean([t.get("net_r", 0.0) for t in wins])) if w_count > 0 else 0.0
    avg_loss_r = float(np.mean([t.get("net_r", 0.0) for t in losses])) if l_count > 0 else 0.0
    
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
            
    # Duration (hours)
    durations = []
    for t in trades:
        e_ts = t.get("entry_timestamp") or t.get("setup_timestamp", 0)
        x_ts = t.get("exit_timestamp") or e_ts
        if x_ts and e_ts and x_ts >= e_ts:
            durations.append((x_ts - e_ts) / 3600.0)
    avg_dur = float(np.mean(durations)) if durations else 0.0
    med_dur = float(np.median(durations)) if durations else 0.0
    
    # MFE / MAE in R-multiples
    mfe_list, mae_list = [], []
    for t in trades:
        entry_p = t.get("entry_price") or t.get("fill_entry_price", 0.0)
        sl_p = t.get("initial_stop_price", 0.0)
        risk_dist = abs(entry_p - sl_p)
        if risk_dist > 0:
            mfe_p = t.get("metadata", {}).get("mfe_price", entry_p)
            mae_p = t.get("metadata", {}).get("mae_price", entry_p)
            mfe_r = abs(mfe_p - entry_p) / risk_dist
            mae_r = abs(mae_p - entry_p) / risk_dist
            mfe_list.append(mfe_r)
            mae_list.append(mae_r)
    avg_mfe = float(np.mean(mfe_list)) if mfe_list else 0.0
    avg_mae = float(np.mean(mae_list)) if mae_list else 0.0
    mfe_conv = (exp_r / avg_mfe) if avg_mfe > 0 else 0.0
    
    # Drawdown
    cum_pnl = np.cumsum([t.get("net_pnl", 0.0) for t in trades])
    peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else np.array([0.0])
    dd_usd = peak - cum_pnl
    max_dd_usd = float(np.max(dd_usd)) if len(dd_usd) > 0 else 0.0
    running_eq = initial_equity + cum_pnl
    eq_peak = np.maximum.accumulate(running_eq) if len(running_eq) > 0 else np.array([initial_equity])
    dd_pct = (eq_peak - running_eq) / eq_peak * 100.0 if len(running_eq) > 0 else np.array([0.0])
    max_dd_pct = float(np.max(dd_pct)) if len(dd_pct) > 0 else 0.0
    
    # Longs / Shorts
    longs = len([t for t in trades if t.get("directional_permission") == "PERMIT_LONG"])
    shorts = len([t for t in trades if t.get("directional_permission") == "PERMIT_SHORT"])
    
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
        
    exit_pcts = {k: (v / t_count * 100.0) for k, v in exit_counts.items()}
    exit_avg_r = {k: float(np.mean(v)) for k, v in exit_r_lists.items()}
    
    # Regime Forensics (HTF macro direction / phase from provenance)
    regimes = {}
    for t in trades:
        prov = t.get("metadata", {}).get("structural_provenance", {})
        macro = prov.get("htf_macro_direction", "UNKNOWN")
        phase = prov.get("htf_phase", "UNKNOWN")
        key = f"{macro} | {phase}"
        if key not in regimes:
            regimes[key] = {"trades": 0, "wins": 0, "pnl": 0.0, "r_sum": 0.0}
        regimes[key]["trades"] += 1
        if t.get("net_pnl", 0.0) > 0:
            regimes[key]["wins"] += 1
        regimes[key]["pnl"] += t.get("net_pnl", 0.0)
        regimes[key]["r_sum"] += t.get("net_r", 0.0)
        
    for k, v in regimes.items():
        v["win_rate"] = (v["wins"] / v["trades"] * 100.0) if v["trades"] > 0 else 0.0
        v["avg_r"] = (v["r_sum"] / v["trades"]) if v["trades"] > 0 else 0.0
        
    return {
        "total_trades": t_count,
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
        "median_duration_hours": med_dur,
        "avg_mfe_r": avg_mfe,
        "avg_mae_r": avg_mae,
        "mfe_to_realized_conversion": mfe_conv,
        "long_trades": longs,
        "short_trades": shorts,
        "exit_attribution": exit_counts,
        "exit_percentages": exit_pcts,
        "exit_avg_r": exit_avg_r,
        "regime_breakdown": regimes
    }


def classify_stream_status(metrics: Dict[str, Any]) -> str:
    n = metrics["total_trades"]
    pf = metrics["profit_factor"]
    exp_r = metrics["expectancy_r"]
    
    if n < 10:
        return "INSUFFICIENT_SAMPLE"
    elif n >= 25 and pf >= 1.35 and exp_r >= 0.15:
        return "STRONG"
    elif n >= 15 and pf >= 1.10 and exp_r > 0.0:
        return "PROMISING"
    elif pf >= 0.95 and exp_r >= -0.05:
        return "MARGINAL"
    else:
        return "WEAK"


def execute_matrix_replay(
    enable_mtf_trailing: bool = True,
    enable_profit_lock: bool = True,
    lockin_r: float = 1.0,
    giveback_r: float = 0.75
) -> Dict[str, Any]:
    
    matrix_data = []
    
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            symbol = f"{asset}USDT"
            tf_set = TimeframeAligner.get_set(tf_set_id)
            
            htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=50000)
            mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=50000)
            ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=50000)
            
            first_ts = ltf_candles[0].timestamp
            last_ts = ltf_candles[-1].timestamp
            first_dt = datetime.fromtimestamp(first_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            last_dt = datetime.fromtimestamp(last_ts, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            
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
                enable_mtf_trailing=enable_mtf_trailing,
                enable_profit_lock=enable_profit_lock,
                lockin_r=lockin_r,
                giveback_r=giveback_r,
                cache_htf_mtf=True,
                risk_config=research_risk_cfg
            )
            
            t0 = time.time()
            results = replayer.run(
                symbol=symbol,
                htf_candles=htf_candles,
                mtf_candles=mtf_candles,
                ltf_candles=ltf_candles
            )
            elapsed = time.time() - t0
            
            closed_trades = results["closed_trades"]
            
            comb_metrics = compute_stream_metrics(closed_trades)
            status_comb = classify_stream_status(comb_metrics)
            
            stream_entry = {
                "symbol": symbol,
                "tf_set_id": tf_set_id,
                "tf_set_label": TF_SET_LABELS[tf_set_id],
                "htf": tf_set.htf,
                "mtf": tf_set.mtf,
                "ltf": tf_set.ltf,
                "candle_counts": {
                    "htf": len(htf_candles),
                    "mtf": len(mtf_candles),
                    "ltf": len(ltf_candles)
                },
                "first_dt": first_dt,
                "last_dt": last_dt,
                "execution_time_sec": elapsed,
                "combined": {
                    "metrics": comb_metrics,
                    "status": status_comb
                },

            }
            matrix_data.append(stream_entry)
            print(f"  [{symbol} | {tf_set_id}] Done in {elapsed:.1f}s | All: {comb_metrics['total_trades']} trades (PF: {comb_metrics['profit_factor']:.2f}, E[R]: {comb_metrics['expectancy_r']:+.2f}R)")
            
    return matrix_data


def main():
    print("=" * 120)
    print("PROJECT TOP1 — GATE 5B: FULL 24-STREAM STRATEGY FORENSIC MATRIX")
    print("=" * 120)
    
    # 1. Run Frozen Control Baseline (All 24 Streams)
    print("\n[PHASE 1: RUNNING FULL 24-STREAM CONTROL BASELINE]...")
    control_matrix = execute_matrix_replay(
        enable_mtf_trailing=True,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75
    )
    
    # 2. Run Ablation Suite
    print("\n" + "=" * 120)
    print("[PHASE 2: RUNNING CONTROLLED ABLATIONS]...")
    print("=" * 120)
    
    # Ablation A: Without +1.0R Profit-Lock
    print("\n[ABLATION A: WITHOUT +1.0R PROFIT-LOCK]...")
    ablation_no_profit_lock = execute_matrix_replay(
        enable_mtf_trailing=True,
        enable_profit_lock=False
    )
    
    # Ablation B: Without MTF Structural Trailing
    print("\n[ABLATION B: WITHOUT MTF STRUCTURAL TRAILING]...")
    ablation_no_mtf_trailing = execute_matrix_replay(
        enable_mtf_trailing=False,
        enable_profit_lock=True,
        lockin_r=1.0,
        giveback_r=0.75
    )
    
    # Bundle all experimental results
    output_bundle = {
        "timestamp_utc": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        "control_baseline_24_streams": control_matrix,
        "ablation_no_profit_lock": ablation_no_profit_lock,
        "ablation_no_mtf_trailing": ablation_no_mtf_trailing
    }
    
    out_file = "/home/mrcn2/crypto-platform/scratch/gate5b_24_stream_forensic_results.json"
    with open(out_file, "w") as f:
        json.dump(output_bundle, f, indent=2)
    print(f"\nSaved full Gate 5B Forensic & Ablation results to {out_file}")


if __name__ == "__main__":
    main()
