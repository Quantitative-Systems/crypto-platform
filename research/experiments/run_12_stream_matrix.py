"""
Product 04 — Research Laboratory: 12-Stream Full Matrix Experiment Runner
Executes the Canonical Three-Timeframe Strategy across:
  - Assets: BTCUSDT, ETHUSDT, SOLUSDT
  - Timeframe Sets:
      SET_1_INVESTING:  1M -> 1W -> 1D
      SET_2_POSITIONAL: 1W -> 1D -> 4H
      SET_3_SWING:      1D -> 4H -> 1H
      SET_4_INTRADAY:   4H -> 1H -> 15M
With Dual MTF Structural Trailing + +1.0R Profit-Lock Protection.
"""

import os
import sys
import json
import time
import numpy as np
from typing import Dict, Any, List

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


def run_stream(
    asset: str,
    tf_set_id: str,
    enable_mtf_trailing: bool = True,
    enable_profit_lock: bool = True,
    lockin_r: float = 1.0,
    giveback_r: float = 0.75,
    limit: int = 50000
) -> Dict[str, Any]:
    symbol = f"{asset}USDT"
    tf_set = TimeframeAligner.get_set(tf_set_id)
    
    # Load candles for all 3 timeframes
    htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=limit)
    mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=limit)
    ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=limit)
    
    # Research mode risk configuration (allows continuous measurement across historical data)
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
    
    start_t = time.time()
    results = replayer.run(
        symbol=symbol,
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )
    elapsed = time.time() - start_t
    
    closed_trades = results["closed_trades"]
    metrics = results["metrics"]
    
    # Compute detailed trade statistics
    t_count = len(closed_trades)
    wins = [t for t in closed_trades if t.get("net_pnl", 0.0) > 0]
    losses = [t for t in closed_trades if t.get("net_pnl", 0.0) <= 0]
    w_count = len(wins)
    l_count = len(losses)
    wr = (w_count / t_count * 100.0) if t_count > 0 else 0.0
    
    gp = sum(t.get("net_pnl", 0.0) for t in wins)
    gl = abs(sum(t.get("net_pnl", 0.0) for t in losses))
    pf = (gp / gl) if gl > 0 else (gp if gp > 0 else 0.0)
    net_pnl = sum(t.get("net_pnl", 0.0) for t in closed_trades)
    
    r_multiples = [t.get("net_r", 0.0) for t in closed_trades]
    total_r = sum(r_multiples)
    avg_r = np.mean(r_multiples) if t_count > 0 else 0.0
    med_r = float(np.median(r_multiples)) if t_count > 0 else 0.0
    avg_win_r = float(np.mean([t.get("net_r", 0.0) for t in wins])) if w_count > 0 else 0.0
    avg_loss_r = float(np.mean([t.get("net_r", 0.0) for t in losses])) if l_count > 0 else 0.0
    
    # Max Drawdown
    equity_curve = results["equity_curve"]
    eq_vals = [e["equity"] for e in equity_curve]
    peak = np.maximum.accumulate(eq_vals) if len(eq_vals) > 0 else np.array([10000.0])
    dd_pct = (peak - eq_vals) / peak * 100.0 if len(eq_vals) > 0 else np.array([0.0])
    max_dd_pct = float(np.max(dd_pct)) if len(dd_pct) > 0 else 0.0
    
    # Max Consecutive Losses
    curr_l = 0
    max_l = 0
    for t in closed_trades:
        if t.get("net_pnl", 0.0) <= 0:
            curr_l += 1
            if curr_l > max_l: max_l = curr_l
        else:
            curr_l = 0
            
    # Exit Reason distribution
    exit_reasons = {}
    for t in closed_trades:
        r = t.get("exit_reason", "UNKNOWN")
        exit_reasons[r] = exit_reasons.get(r, 0) + 1
        

    return {
        "symbol": symbol,
        "tf_set_id": tf_set_id,
        "tf_set_label": TF_SET_LABELS[tf_set_id],
        "candles_processed": len(ltf_candles),
        "execution_time_sec": elapsed,
        "total_trades": t_count,
        "wins": w_count,
        "losses": l_count,
        "win_rate_pct": wr,
        "gross_profit": gp,
        "gross_loss": gl,
        "profit_factor": pf,
        "net_pnl": net_pnl,
        "total_realized_r": total_r,
        "avg_realized_r": avg_r,
        "median_realized_r": med_r,
        "avg_win_r": avg_win_r,
        "avg_loss_r": avg_loss_r,
        "max_drawdown_pct": max_dd_pct,
        "max_consecutive_losses": max_l,
        "exit_reasons": exit_reasons,

        "closed_trades": closed_trades
    }


def main():
    print("=" * 100)
    print("CANONICAL 12-STREAM MATRIX HISTORICAL BACKTEST (DAY 35 REFINEMENT)")
    print("=" * 100)
    
    matrix_results = []
    
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            print(f"\n[EXECUTING STREAM] {asset}USDT | {TF_SET_LABELS[tf_set_id]}...")
            res = run_stream(
                asset=asset,
                tf_set_id=tf_set_id,
                enable_mtf_trailing=True,
                enable_profit_lock=True,
                lockin_r=1.0,
                giveback_r=0.75,
                limit=50000
            )
            matrix_results.append(res)
            print(f"  -> Trades: {res['total_trades']} | WR: {res['win_rate_pct']:.2f}% | PF: {res['profit_factor']:.2f} | Net PnL: ${res['net_pnl']:+,.2f} | Avg R: {res['avg_realized_r']:+.2f}R | Exits: {res['exit_reasons']}")

    # Save summary JSON
    summary_path = "/home/mrcn2/crypto-platform/scratch/canonical_12_stream_matrix_results.json"
    # Clean non-serializable elements before export
    clean_results = []
    for r in matrix_results:
        cr = {k: v for k, v in r.items() if k != "closed_trades"}
        clean_results.append(cr)
        
    with open(summary_path, "w") as f:
        json.dump(clean_results, f, indent=2)
        
    print(f"\nSaved full matrix results to {summary_path}")


if __name__ == "__main__":
    main()
