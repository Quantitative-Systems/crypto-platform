"""
Product 04 — Research Laboratory: Gate 5 Out-Of-Sample (OOS) Validation & Integrity Audit
Executes frozen canonical strategy across In-Sample (IS: 70%) and Out-Of-Sample (OOS: 30%) partitions:
  - Assets: BTCUSDT, ETHUSDT, SOLUSDT
  - Timeframe Sets:
      SET_3_SWING:      1D -> 4H -> 1H (50,000 LTF candles)
      SET_4_INTRADAY:   4H -> 1H -> 15M (50,000 LTF candles)
      UNIFIED_STRATEGY
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
import numpy as np
from typing import Dict, Any, List, Tuple

from market_data.warehouse_loader import WarehouseLoader
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from risk_engine.contracts.risk_config import RiskConfig


ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_3", "SET_4"]

TF_SET_LABELS = {
    "SET_3": "SET_3_SWING (1D -> 4H -> 1H)",
    "SET_4": "SET_4_INTRADAY (4H -> 1H -> 15M)"
}


def analyze_trade_set(trades: List[Dict[str, Any]], equity_curve: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    t_count = len(trades)
    if t_count == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
            "total_realized_r": 0.0, "expectancy_r": 0.0, "median_r": 0.0,
            "avg_win_r": 0.0, "avg_loss_r": 0.0, "max_drawdown_pct": 0.0,
            "long_trades": 0, "short_trades": 0,
            "exit_attribution": {}, "exit_avg_r": {}
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
    
    # Longs vs Shorts
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
        
    exit_avg_r = {k: float(np.mean(v)) for k, v in exit_r_lists.items()}
    
    # Max Drawdown from trade PnL sequence
    cum_pnl = np.cumsum([t.get("net_pnl", 0.0) for t in trades])
    peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else np.array([0.0])
    dd = peak - cum_pnl
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0
    
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
        "max_drawdown_usd": max_dd,
        "long_trades": longs,
        "short_trades": shorts,
        "exit_attribution": exit_counts,
        "exit_avg_r": exit_avg_r
    }


def run_is_oos_experiment(asset: str, tf_set_id: str, split_ratio: float = 0.70) -> Dict[str, Any]:
    symbol = f"{asset}USDT"
    tf_set = TimeframeAligner.get_set(tf_set_id)
    
    # 1. Load full datasets
    htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=50000)
    mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=50000)
    ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=50000)
    
    total_ltf = len(ltf_candles)
    split_idx = int(total_ltf * split_ratio)
    split_timestamp = ltf_candles[split_idx].timestamp
    
    split_dt = datetime.fromtimestamp(split_timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    start_dt = datetime.fromtimestamp(ltf_candles[0].timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    end_dt = datetime.fromtimestamp(ltf_candles[-1].timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # 2. Run Causal Replayer across full chronological data (preserves warm-up and continuous state)
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
    
    all_trades = results["closed_trades"]
    
    # 3. Partition trades based on setup_timestamp relative to split_timestamp
    is_trades = [t for t in all_trades if t.get("setup_timestamp", 0) < split_timestamp]
    oos_trades = [t for t in all_trades if t.get("setup_timestamp", 0) >= split_timestamp]
    
    # Compute stats for Overall, IS, and OOS
    is_stats_all = analyze_trade_set(is_trades)
    oos_stats_all = analyze_trade_set(oos_trades)
    

    
    # Compute Decay / Retention Metrics
    # Retention = OOS_metric / IS_metric
    wr_retention = (oos_stats_all["win_rate_pct"] / is_stats_all["win_rate_pct"]) if is_stats_all["win_rate_pct"] > 0 else 0.0
    pf_retention = (oos_stats_all["profit_factor"] / is_stats_all["profit_factor"]) if is_stats_all["profit_factor"] > 0 else 0.0
    exp_retention = (oos_stats_all["expectancy_r"] / is_stats_all["expectancy_r"]) if is_stats_all["expectancy_r"] > 0 else 0.0
    
    # Calculate setup age metrics from trade metadata
    setup_ages_hours = []
    for t in all_trades:
        prov = t.get("metadata", {}).get("structural_provenance", {})
        if prov:
            c_ts = prov.get("htf_context_timestamp", 0)
            e_ts = t.get("entry_timestamp", 0) or t.get("setup_timestamp", 0)
            if c_ts and e_ts and e_ts >= c_ts:
                age_h = (e_ts - c_ts) / 3600.0
                setup_ages_hours.append(age_h)
                
    mean_age_h = float(np.mean(setup_ages_hours)) if setup_ages_hours else 0.0
    max_age_h = float(np.max(setup_ages_hours)) if setup_ages_hours else 0.0
    
    # Classification Status
    # OOS_SUPPORTED: OOS Trades >= 20, PF >= 1.20, E[R] > 0
    # OOS_MARGINAL: OOS Trades >= 10, 1.0 <= PF < 1.20 or E[R] slightly positive
    # OOS_FAILED: OOS PF < 1.0 or E[R] < 0
    # INSUFFICIENT_SAMPLE: OOS Trades < 10
    if oos_stats_all["total_trades"] < 10:
        status = "INSUFFICIENT_SAMPLE"
    elif oos_stats_all["profit_factor"] >= 1.20 and oos_stats_all["expectancy_r"] > 0.0:
        status = "OOS_SUPPORTED"
    elif oos_stats_all["profit_factor"] >= 1.0 and oos_stats_all["expectancy_r"] >= 0.0:
        status = "OOS_MARGINAL"
    else:
        status = "OOS_FAILED"
        
    return {
        "symbol": symbol,
        "tf_set_id": tf_set_id,
        "tf_set_label": TF_SET_LABELS[tf_set_id],
        "start_dt": start_dt,
        "split_dt": split_dt,
        "end_dt": end_dt,
        "total_candles": total_ltf,
        "is_candles": split_idx,
        "oos_candles": total_ltf - split_idx,
        "execution_time_sec": elapsed,
        "status": status,
        "is_stats": {
            "combined": is_stats_all
        },
        "oos_stats": {
            "combined": oos_stats_all
        },
        "retention": {
            "wr_retention": wr_retention,
            "pf_retention": pf_retention,
            "exp_retention": exp_retention
        },
        "setup_lifecycle": {
            "mean_setup_age_hours": mean_age_h,
            "max_setup_age_hours": max_age_h,
            "total_trades_analyzed": len(all_trades)
        }
    }


def main():
    print("=" * 100)
    print("GATE 5: OUT-OF-SAMPLE (OOS) VALIDATION & STRATEGY INTEGRITY AUDIT")
    print("=" * 100)
    
    oos_results = []
    
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            print(f"\n[RUNNING VALIDATION] {asset}USDT | {TF_SET_LABELS[tf_set_id]}...")
            res = run_is_oos_experiment(asset=asset, tf_set_id=tf_set_id, split_ratio=0.70)
            oos_results.append(res)
            
            is_c = res["is_stats"]["combined"]
            oos_c = res["oos_stats"]["combined"]
            ret = res["retention"]
            
            print(f"  IS  -> Trades: {is_c['total_trades']:3d} | WR: {is_c['win_rate_pct']:5.2f}% | PF: {is_c['profit_factor']:5.2f} | E[R]: {is_c['expectancy_r']:+5.2f}R | Realized R: {is_c['total_realized_r']:+8.2f}R")
            print(f"  OOS -> Trades: {oos_c['total_trades']:3d} | WR: {oos_c['win_rate_pct']:5.2f}% | PF: {oos_c['profit_factor']:5.2f} | E[R]: {oos_c['expectancy_r']:+5.2f}R | Realized R: {oos_c['total_realized_r']:+8.2f}R")
            print(f"  RET -> WR Ret: {ret['wr_retention']:.2f}x | PF Ret: {ret['pf_retention']:.2f}x | Exp Ret: {ret['exp_retention']:.2f}x | Status: [{res['status']}]")

    # Save to JSON artifact
    out_path = "/home/mrcn2/crypto-platform/scratch/gate5_oos_validation_results.json"
    with open(out_path, "w") as f:
        json.dump(oos_results, f, indent=2)
    print(f"\nSaved Gate 5 OOS validation results to {out_path}")


if __name__ == "__main__":
    main()
