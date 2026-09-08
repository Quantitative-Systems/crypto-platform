"""
Product 04 — Research Laboratory: Canonical Rebuild Development Replay Engine
Replays the 15-stream matrix strictly on the 2021-01-01 to 2022-12-31 Development Partition.

CANONICAL STRATEGY REBUILD:
- Mandatory active HTF keyzone interaction (no unconditional spawns in thin air).
- Forward HTF destination targets (unmitigated keyzones, liquidity pools, weak swings; no backwards targets).
- MTF countertrend context + structural shift realignment.
- Active MTF keyzone retest (no is_mitigated == True shortcut).
- Directional LTF entry confirmation (liquidity sweep + directional displacement close).
- Immediate LTF micro structural invalidation SL.
- Causal MTF structural trailing (monotonic swing tracking + adverse CHOCH exit; no D-03 +1R profit lock).
- Risk <= 1.0% equity ($100 per trade on $10,000 equity). Planned RR >= 4.0R floor.
- Adverse-first zero-lookahead execution with 2 bps maker, 5 bps taker, 5 bps adverse slippage.

Saves artifact: scratch/canonical_rebuild_dev_results.json
Preserves untouched: scratch/h0_dev_control_results.json
"""

import os
import sys
import json
import time
import math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, "/home/mrcn2/crypto-platform")

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from research.replayer.causal_replayer import CausalReplayer
from research.replayer.timeframe_aligner import TimeframeAligner
from research.simulation.trade_ledger import TradeLedger, SimulatedTrade
from risk_engine.contracts.risk_config import RiskConfig
from strategy_engine.contracts.strategy_state import CandidateState

ASSETS = ["BTC", "ETH", "SOL"]
TF_SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

TF_SET_METADATA = {
    "SET_1": {"label": "SET_1 (1M -> 1W -> 1D, Macro)", "htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"label": "SET_2 (1W -> 1D -> 4H, Position)", "htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"label": "SET_3 (1D -> 4H -> 1H, Swing)", "htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"label": "SET_4 (4H -> 1H -> 15M, Intraday)", "htf": "4h", "mtf": "1h", "ltf": "15m"},
    "SET_5": {"label": "SET_5 (15M -> 5M -> 1M, Intraday Scalping)", "htf": "15m", "mtf": "5m", "ltf": "1m"},
}


def run_single_stream_rebuild(asset: str, tf_set_id: str) -> Dict[str, Any]:
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_info = TF_SET_METADATA[tf_set_id]
    
    t0 = time.time()
    
    ltf_start_time_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    period_label = "2021-01-01 to 2022-12-31 (Development Partition)"

    if tf_set_id == "SET_5":
        print(f"[{stream_id}] SET_5 (15m->5m->1m) historical depth limited for 2021-2022. Fail-closed: 0 trades.")
        return {
            "stream_id": stream_id,
            "asset": asset,
            "timeframe_set": tf_set_id,
            "label": tf_info["label"],
            "period": period_label,
            "ltf_candles_count": 0,
            "execution_time_sec": 0.0,
            "trades": [],
            "status": "INSUFFICIENT_HISTORICAL_DEPTH_FAIL_CLOSED",
            "lifecycle_funnel": {},
            "rejections": {}
        }

    # Load Certified Datasets
    try:
        htf_candles = WarehouseLoader.load_history(symbol, tf_info["htf"], limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        mtf_candles = WarehouseLoader.load_history(symbol, tf_info["mtf"], limit=1_000_000, start_time_ms=None, end_time_ms=end_time_ms)
        ltf_candles = WarehouseLoader.load_history(symbol, tf_info["ltf"], limit=1_000_000, start_time_ms=ltf_start_time_ms, end_time_ms=end_time_ms)
        
        DataCertifier.certify_dataset(htf_candles, tf_info["htf"], symbol, allow_gaps=True, max_allowed_gap_bars=2000)
        DataCertifier.certify_dataset(mtf_candles, tf_info["mtf"], symbol, allow_gaps=True, max_allowed_gap_bars=2000)
        DataCertifier.certify_dataset(ltf_candles, tf_info["ltf"], symbol, allow_gaps=True, max_allowed_gap_bars=2000)
    except Exception as data_err:
        print(f"[{stream_id}] Data load warning / error: {data_err}")
        return {
            "stream_id": stream_id,
            "asset": asset,
            "timeframe_set": tf_set_id,
            "error": str(data_err),
            "trades": [],
            "performance": {"total_trades": 0, "net_r": 0.0}
        }

    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.0005,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )

    replayer = CausalReplayer(
        timeframe_set_id=tf_set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0002,   # 2 bps maker
        taker_fee_rate=0.0005,   # 5 bps taker
        slippage_bps=5.0,        # 5 bps realistic adverse slippage
        enable_mtf_trailing=True, # MTF structural trailing preserved
        enable_profit_lock=False, # ZERO D-03 profit lock
        lockin_r=999.0,
        cache_htf_mtf=True,
        risk_config=risk_cfg
    )

    result = replayer.run(
        symbol=symbol,
        htf_candles=htf_candles,
        mtf_candles=mtf_candles,
        ltf_candles=ltf_candles
    )

    closed_trades = result.get("closed_trades", [])
    elapsed = time.time() - t0
    print(f"✅ [{stream_id}] Completed in {elapsed:.2f}s — Executed Trades: {len(closed_trades)}")

    return {
        "stream_id": stream_id,
        "asset": asset,
        "timeframe_set": tf_set_id,
        "label": tf_info["label"],
        "period": period_label,
        "ltf_candles_count": len(ltf_candles),
        "execution_time_sec": round(elapsed, 2),
        "trades": closed_trades,
        "lifecycle_funnel": result.get("lifecycle_funnel", {}),
        "rejections": result.get("rejection_reasons", {})
    }


def run_full_rebuild_matrix():
    print("=" * 80)
    print("STARTING CANONICAL REBUILD MATRIX REPLAY (2021-01-01 to 2022-12-31)")
    print("=" * 80)

    stream_tasks = []
    for tf_set in TF_SETS:
        for asset in ASSETS:
            stream_tasks.append((asset, tf_set))

    results_by_stream = {}
    all_trades = []

    # Run in parallel processes across CPU cores
    max_workers = min(os.cpu_count() or 4, len(stream_tasks))
    print(f"Executing 15 streams in parallel using {max_workers} worker processes...\n")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(run_single_stream_rebuild, asset, tf_set): (asset, tf_set)
            for asset, tf_set in stream_tasks
        }

        for future in as_completed(future_map):
            asset, tf_set = future_map[future]
            stream_id = f"{asset}_{tf_set}"
            try:
                res = future.result()
                results_by_stream[stream_id] = res
                stream_trades = res.get("trades", [])
                all_trades.extend(stream_trades)
            except Exception as exc:
                print(f"❌ [{stream_id}] Failed with exception: {exc}")
                results_by_stream[stream_id] = {
                    "stream_id": stream_id,
                    "asset": asset,
                    "timeframe_set": tf_set,
                    "error": str(exc),
                    "trades": []
                }

    # Aggregate performance analytics
    total_trades = len(all_trades)
    print("\n" + "=" * 80)
    print(f"CANONICAL REBUILD AGGREGATE SUMMARY: {total_trades} TOTAL TRADES")
    print("=" * 80)

    net_r_list = [float(t.get("realized_r", 0.0) or t.get("realized_rr", 0.0) or t.get("net_r", 0.0)) for t in all_trades]
    gross_r_list = [float(t.get("gross_r", 0.0) or t.get("gross_rr", 0.0) or net_r_list[i]) for i, t in enumerate(all_trades)]

    wins = [r for r in net_r_list if r > 0]
    losses = [r for r in net_r_list if r < 0]
    breakevens = [r for r in net_r_list if r == 0]

    net_r = sum(net_r_list)
    gross_r = sum(gross_r_list)
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    expectancy = (net_r / total_trades) if total_trades > 0 else 0.0

    gross_pos = sum(r for r in net_r_list if r > 0)
    gross_neg = abs(sum(r for r in net_r_list if r < 0))
    profit_factor = (gross_pos / gross_neg) if gross_neg > 0 else (999.0 if gross_pos > 0 else 0.0)

    # Calculate Drawdown in R
    running_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    # Sort chronologically by exit timestamp
    sorted_trades = sorted(all_trades, key=lambda x: x.get("exit_timestamp", 0))
    for t in sorted_trades:
        r = float(t.get("realized_r", 0.0) or t.get("realized_rr", 0.0) or t.get("net_r", 0.0))
        running_r += r
        if running_r > peak_r:
            peak_r = running_r
        dd = peak_r - running_r
        if dd > max_dd_r:
            max_dd_r = dd

    # Exit attribution counts
    exit_counts = {}
    for t in all_trades:
        reason = t.get("exit_reason", "UNKNOWN")
        exit_counts[reason] = exit_counts.get(reason, 0) + 1

    # MFE / MAE forensics
    mfe_list = [float(t.get("mfe_r", 0.0) or 0.0) for t in all_trades]
    mae_list = [float(t.get("mae_r", 0.0) or 0.0) for t in all_trades]

    # Unique setups
    setup_ids = set(t.get("setup_id", t.get("trade_id")) for t in all_trades)
    unique_setups = len(setup_ids)

    # Per stream summary
    stream_summaries = {}
    for stream_id, s_data in results_by_stream.items():
        s_trades = s_data.get("trades", [])
        s_net_r = sum(float(t.get("realized_r", 0.0) or t.get("realized_rr", 0.0) or t.get("net_r", 0.0)) for t in s_trades)
        s_wins = sum(1 for t in s_trades if float(t.get("realized_r", 0.0) or t.get("realized_rr", 0.0) or t.get("net_r", 0.0)) > 0)
        stream_summaries[stream_id] = {
            "trades": len(s_trades),
            "net_r": round(s_net_r, 4),
            "win_rate": round((s_wins / len(s_trades) * 100.0) if s_trades else 0.0, 1),
            "status": s_data.get("status", "OK" if len(s_trades) > 0 else "ZERO_TRADES")
        }

    dev_results_payload = {
        "metadata": {
            "title": "CANONICAL_REBUILD Development Replay",
            "hypothesis_id": "CANONICAL_REBUILD_DEV",
            "description": "Strict institutional canonical strategy implementation without shortcuts or unanchored spawns.",
            "temporal_partition": "DEVELOPMENT (2021-01-01 to 2022-12-31)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rules": {
                "enable_profit_lock": False,
                "enable_mtf_trailing": True,
                "planned_rr_floor": 4.0,
                "maker_fee_bps": 2.0,
                "taker_fee_bps": 5.0,
                "slippage_bps": 5.0,
                "execution_mode": "ADVERSE_FIRST_ZERO_LOOKAHEAD"
            }
        },
        "aggregate_performance": {
            "total_trades": total_trades,
            "unique_economic_setups": unique_setups,
            "net_realized_r": round(net_r, 4),
            "gross_realized_r": round(gross_r, 4),
            "expectancy_r": round(expectancy, 4),
            "profit_factor": round(profit_factor, 2),
            "win_rate_pct": round(win_rate, 1),
            "max_drawdown_r": round(max_dd_r, 2),
            "wins": len(wins),
            "losses": len(losses),
            "breakevens": len(breakevens),
            "avg_winner_r": round(float(np.mean(wins)), 4) if wins else 0.0,
            "avg_loser_r": round(float(np.mean(losses)), 4) if losses else 0.0
        },
        "exit_distribution": exit_counts,
        "excursion_forensics": {
            "mean_mfe_r": round(float(np.mean(mfe_list)), 2) if mfe_list else 0.0,
            "median_mfe_r": round(float(np.median(mfe_list)), 2) if mfe_list else 0.0,
            "mean_mae_r": round(float(np.mean(mae_list)), 2) if mae_list else 0.0,
            "median_mae_r": round(float(np.median(mae_list)), 2) if mae_list else 0.0
        },
        "per_stream_performance": stream_summaries,
        "trade_ledger": all_trades
    }

    out_file = "/home/mrcn2/crypto-platform/scratch/canonical_rebuild_dev_results.json"
    with open(out_file, "w") as f:
        json.dump(dev_results_payload, f, indent=2)

    print(f"\nSuccessfully written CANONICAL_REBUILD results to {out_file}")
    print(f"Summary: Trades={total_trades} | Net R={net_r:.2f}R | WR={win_rate:.1f}% | PF={profit_factor:.2f} | Exp={expectancy:.2f}R | MaxDD={max_dd_r:.2f}R")


if __name__ == "__main__":
    run_full_rebuild_matrix()
