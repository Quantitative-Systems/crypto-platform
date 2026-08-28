"""
Product 04 — Research Laboratory: Full Strategy Forensic Matrix (Unified Contexts)
Executes the Frozen Canonical Unified State Machine across:
  - 3 Assets: BTCUSDT, ETHUSDT, SOLUSDT
  - 4 Timeframe Sets
Total = 12 Streams. Splits performance metrics into PULLBACK and CONTINUATION contexts.
"""

import json
import time
from datetime import datetime, timezone
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


def compute_stream_metrics(trades: List[Dict[str, Any]], initial_equity: float = 10000.0) -> Dict[str, Any]:
    t_count = len(trades)
    if t_count == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "profit_factor": 0.0, "net_pnl": 0.0,
            "total_realized_r": 0.0, "expectancy_r": 0.0, "median_r": 0.0,
            "avg_win_r": 0.0, "avg_loss_r": 0.0, "max_drawdown_usd": 0.0, "max_drawdown_pct": 0.0,
            "avg_mfe_r": 0.0, "avg_mae_r": 0.0
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
    
    cum_pnl = np.cumsum([t.get("net_pnl", 0.0) for t in trades])
    peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else np.array([0.0])
    dd_usd = peak - cum_pnl
    max_dd_usd = float(np.max(dd_usd)) if len(dd_usd) > 0 else 0.0
    running_eq = initial_equity + cum_pnl
    eq_peak = np.maximum.accumulate(running_eq) if len(running_eq) > 0 else np.array([initial_equity])
    dd_pct = (eq_peak - running_eq) / eq_peak * 100.0 if len(running_eq) > 0 else np.array([0.0])
    max_dd_pct = float(np.max(dd_pct)) if len(dd_pct) > 0 else 0.0
        
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
        "avg_mfe_r": avg_mfe,
        "avg_mae_r": avg_mae
    }


def execute_matrix_replay() -> Dict[str, Any]:
    matrix_data = []
    
    total_trades_all = 0
    
    print("=" * 100)
    print("RUNNING UNIFIED MATRIX: 3 ASSETS x 4 TIMEFRAMES")
    print("=" * 100)
    
    from market_data.data_certifier import DataCertifier
    
    # Base simulation period (LTF start)
    ltf_start_time_ms = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    
    for asset in ASSETS:
        for tf_set_id in TF_SETS:
            symbol = f"{asset}USDT"
            tf_set = TimeframeAligner.get_set(tf_set_id)
            
            print(f"Loading certified dataset for {symbol} | {tf_set_id}...")
            
            # Fetch all available warmup data for HTF and MTF
            htf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.htf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
            mtf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.mtf, limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
            
            # LTF is tightly bounded to the simulation period
            ltf_candles = WarehouseLoader.load_history(f"{asset}/USDT", tf_set.ltf, limit=1_000_000, start_time_ms=ltf_start_time_ms, end_time_ms=end_time_ms)
            
            # Certification Check
            try:
                DataCertifier.certify_dataset(htf_candles, tf_set.htf, symbol, allow_gaps=True)
                DataCertifier.certify_dataset(mtf_candles, tf_set.mtf, symbol, allow_gaps=True)
                DataCertifier.certify_dataset(ltf_candles, tf_set.ltf, symbol, allow_gaps=True)
                DataCertifier.certify_overlap(htf_candles, mtf_candles, ltf_candles, min_lookback_bars=30)
            except ValueError as e:
                print(f"❌ Data Certification Failed for {symbol} {tf_set_id}: {e}")
                continue
            
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
            
            total_trades_all += len(closed_trades)
            
            stream_entry = {
                "symbol": symbol,
                "tf_set_id": tf_set_id,
                "execution_time_sec": elapsed,
                "combined": comb_metrics
            }
            matrix_data.append(stream_entry)
            print(f"  [{symbol} | {tf_set_id}] {elapsed:.1f}s | Trades: {comb_metrics['total_trades']}")
            
    print("-" * 100)
    print(f"TOTAL TRADES ACROSS MATRIX: {total_trades_all}")
    
    return matrix_data


def main():
    matrix_results = execute_matrix_replay()
    
    out_file = "/home/mrcn2/crypto-platform/scratch/unified_context_matrix_results.json"
    with open(out_file, "w") as f:
        json.dump(matrix_results, f, indent=2)
    print(f"\nSaved matrix results to {out_file}")

if __name__ == "__main__":
    main()
