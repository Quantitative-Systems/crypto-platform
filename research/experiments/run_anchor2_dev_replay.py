"""
Product 04 — Research Laboratory: Isolated D-03 Development Replay Engine
Replays the 15-stream matrix strictly on the 2021-01-01 to 2022-12-31 Development Partition.

HYPOTHESIS H0_DEV_CONTROL:
- Pure unmodified canonical strategy on the exact 2021-2022 dataset.
- NO D-03 post-entry breakeven lock.
  - Entry logic (Unchanged)
  - HTF structure / trend / destination (Unchanged)
  - MTF realignment / keyzone / retest (Unchanged)
  - LTF liquidity sweep / displacement / trigger (Unchanged)
  - Initial SL (Unchanged)
  - Planned RR >= 4.0R floor (Unchanged)
  - Risk <= 1.0% equity ($100 per trade on $10,000 equity)
  - Adverse-first intrabar collision resolution
  - Real Maker (2 bps) / Taker (5 bps) fees + 5 bps adverse slippage
  - Zero lookahead protection

Saves artifact: scratch/h0_dev_control_results.json
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


def run_single_stream_dev(asset: str, tf_set_id: str) -> Dict[str, Any]:
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_info = TF_SET_METADATA[tf_set_id]
    
    t0 = time.time()
    
    # Strictly 2021-01-01 to 2022-12-31 (2 full calendar years Development Partition)
    ltf_start_time_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    period_label = "2021-01-01 to 2022-12-31 (Development Partition)"

    if tf_set_id == "SET_5":
        # 1m/5m public Binance historical depth is limited to 2026 certified cache
        print(f"[{stream_id}] SET_5 (15m->5m->1m) has insufficient historical depth for 2021-2022. Fail-closed: 0 trades.")
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

    # Configure Isolated D-03 Replayer
    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.001,
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
        enable_profit_lock=False, # DISABLED FOR H0 CONTROL
        lockin_r=999.0,           # Disable secondary ratchet to isolate D-03
        cache_htf_mtf=True,
        risk_config=risk_cfg
    )

    # Run Causal Replay
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


def run_full_dev_matrix():
    print("=" * 80)
    print("STARTING H0_DEV_CONTROL MATRIX REPLAY (2021-01-01 to 2022-12-31)")
    print("=" * 80)

    stream_tasks = []
    for tf_set in TF_SETS:
        for asset in ASSETS:
            stream_tasks.append((asset, tf_set))

    results = []
    # Execute in parallel with ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(8, len(stream_tasks))) as executor:
        future_map = {executor.submit(run_single_stream_dev, asset, tf_set): (asset, tf_set) for asset, tf_set in stream_tasks}
        for future in as_completed(future_map):
            asset, tf_set = future_map[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                print(f"❌ Error on {asset}_{tf_set}: {e}")

    # Consolidate metrics across all 15 streams
    all_trades = []
    for r in results:
        stream_id = r["stream_id"]
        for t in r.get("trades", []):
            t_copy = dict(t)
            t_copy["stream_id"] = stream_id
            all_trades.append(t_copy)

    total_trades = len(all_trades)
    print(f"\nConsolidated Total Trades across 15 Development Streams: {total_trades}")

    # Compute detailed forensic trade metrics
    wins = [t for t in all_trades if float(t.get("realized_r", 0.0)) > 0]
    losses = [t for t in all_trades if float(t.get("realized_r", 0.0)) <= 0]
    
    net_r = sum(float(t.get("realized_r", 0.0)) for t in all_trades)
    gross_r = sum(float(t.get("gross_r", 0.0)) for t in all_trades)
    expectancy = net_r / total_trades if total_trades > 0 else 0.0

    gross_win_r = sum(float(t.get("realized_r", 0.0)) for t in wins)
    gross_loss_r = abs(sum(float(t.get("realized_r", 0.0)) for t in losses))
    profit_factor = gross_win_r / gross_loss_r if gross_loss_r > 0 else (999.0 if gross_win_r > 0 else 0.0)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0.0

    # Max Drawdown calculation in R
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    for t in all_trades:
        cum_r += float(t.get("realized_r", 0.0))
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd_r:
            max_dd_r = dd

    # Exit reason counts
    exit_counts = {}
    for t in all_trades:
        reason = t.get("exit_reason", "UNKNOWN")
        exit_counts[reason] = exit_counts.get(reason, 0) + 1

    # Unique economic setups
    setup_keys = set()
    for t in all_trades:
        key = (t.get("stream_id"), t.get("candidate_timestamp"), t.get("entry"), t.get("sl"), t.get("tp"))
        setup_keys.add(key)
    unique_setups = len(setup_keys)

    # Excursion analysis
    mfe_list = []
    mae_list = []
    reached_1r_count = 0
    protected_by_d03_count = 0

    for t in all_trades:
        entry_p = float(t.get("entry", 0.0))
        sl_p = float(t.get("sl", 0.0))
        risk_dist = abs(entry_p - sl_p)
        exit_reason = t.get("exit_reason")
        
        # MFE & MAE from metadata if present
        meta = t.get("metadata", {})
        mfe_p = meta.get("mfe_price", entry_p)
        mae_p = meta.get("mae_price", entry_p)
        is_long = (t.get("htf_bias") == "PERMIT_LONG")
        
        if risk_dist > 0:
            if is_long:
                mfe_r = (mfe_p - entry_p) / risk_dist
                mae_r = (entry_p - mae_p) / risk_dist
            else:
                mfe_r = (entry_p - mfe_p) / risk_dist
                mae_r = (mae_p - entry_p) / risk_dist
        else:
            mfe_r = 0.0
            mae_r = 0.0

        mfe_list.append(round(mfe_r, 2))
        mae_list.append(round(mae_r, 2))

        if mfe_r >= 1.0:
            reached_1r_count += 1
        if exit_reason == "PROFIT_LOCK_TRAIL":
            protected_by_d03_count += 1

    # Per-stream breakdown
    stream_summaries = {}
    for r in results:
        sid = r["stream_id"]
        str_trades = r.get("trades", [])
        str_net_r = sum(float(t.get("realized_r", 0.0)) for t in str_trades)
        str_wins = sum(1 for t in str_trades if float(t.get("realized_r", 0.0)) > 0)
        stream_summaries[sid] = {
            "trades": len(str_trades),
            "wins": str_wins,
            "losses": len(str_trades) - str_wins,
            "win_rate_pct": round(str_wins / len(str_trades) * 100, 1) if str_trades else 0.0,
            "net_r": round(str_net_r, 4),
            "expectancy_r": round(str_net_r / len(str_trades), 4) if str_trades else 0.0
        }

    # Per-regime breakdown (Bull / Bear / Chop based on 2021-2022 quarters)
    regime_breakdown = {
        "2021_BULL_MARKET (2021-01-01 to 2021-11-10)": {"trades": 0, "net_r": 0.0, "wins": 0},
        "2022_BEAR_MARKET (2021-11-11 to 2022-12-31)": {"trades": 0, "net_r": 0.0, "wins": 0}
    }
    for t in all_trades:
        ts = t.get("candidate_timestamp", 0)
        if ts < 1636588800: # 2021-11-11
            reg = "2021_BULL_MARKET (2021-01-01 to 2021-11-10)"
        else:
            reg = "2022_BEAR_MARKET (2021-11-11 to 2022-12-31)"
        regime_breakdown[reg]["trades"] += 1
        regime_breakdown[reg]["net_r"] += float(t.get("realized_r", 0.0))
        if float(t.get("realized_r", 0.0)) > 0:
            regime_breakdown[reg]["wins"] += 1

    for k in regime_breakdown:
        cnt = regime_breakdown[k]["trades"]
        wn = regime_breakdown[k]["wins"]
        regime_breakdown[k]["net_r"] = round(regime_breakdown[k]["net_r"], 4)
        regime_breakdown[k]["win_rate_pct"] = round(wn / cnt * 100, 1) if cnt > 0 else 0.0
        regime_breakdown[k]["expectancy_r"] = round(regime_breakdown[k]["net_r"] / cnt, 4) if cnt > 0 else 0.0

    # Assemble complete dev result artifact
    dev_results_payload = {
        "metadata": {
            "title": "H0_DEV_CONTROL Baseline Development Replay",
            "hypothesis_id": "H0_DEV_CONTROL",
            "description": "Pure unmodified H0 baseline on 2021-2022. No D-03 lock.",
            "temporal_partition": "DEVELOPMENT (2021-01-01 to 2022-12-31)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": "e9cc4b7",
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
            "total_friction_r": round(gross_r - net_r, 4)
        },
        "exit_distribution": {
            "initial_sl_exits": exit_counts.get("INITIAL_LTF_SL", 0),
            "breakeven_profit_lock_exits": exit_counts.get("PROFIT_LOCK_TRAIL", 0),
            "mtf_structural_trail_exits": exit_counts.get("MTF_STRUCTURAL_TRAIL", 0),
            "htf_target_exits": exit_counts.get("HTF_TP", 0)
        },
        "excursion_forensics": {
            "trades_reaching_plus_1R": reached_1r_count,
            "trades_protected_by_d03": protected_by_d03_count,
            "mean_mfe_r": round(float(np.mean(mfe_list)), 2) if mfe_list else 0.0,
            "median_mfe_r": round(float(np.median(mfe_list)), 2) if mfe_list else 0.0,
            "mean_mae_r": round(float(np.mean(mae_list)), 2) if mae_list else 0.0,
            "median_mae_r": round(float(np.median(mae_list)), 2) if mae_list else 0.0,
            "mfe_distribution": {
                "0.0R_to_0.5R": sum(1 for x in mfe_list if 0.0 <= x < 0.5),
                "0.5R_to_1.0R": sum(1 for x in mfe_list if 0.5 <= x < 1.0),
                "1.0R_to_2.0R": sum(1 for x in mfe_list if 1.0 <= x < 2.0),
                "2.0R_to_4.0R": sum(1 for x in mfe_list if 2.0 <= x < 4.0),
                "4.0R_plus": sum(1 for x in mfe_list if x >= 4.0)
            },
            "mae_distribution": {
                "0.0R_to_0.5R": sum(1 for x in mae_list if 0.0 <= x < 0.5),
                "0.5R_to_1.0R": sum(1 for x in mae_list if 0.5 <= x < 1.0),
                "1.0R_to_1.5R": sum(1 for x in mae_list if 1.0 <= x < 1.5),
                "1.5R_plus": sum(1 for x in mae_list if x >= 1.5)
            }
        },
        "per_stream_performance": stream_summaries,
        "per_regime_performance": regime_breakdown,
        "trade_ledger": all_trades
    }

    out_file = "/home/mrcn2/crypto-platform/scratch/anchor2_dev_results.json"
    with open(out_file, "w") as f:
        json.dump(dev_results_payload, f, indent=2)

    print(f"\nSuccessfully written H0_DEV_CONTROL results to {out_file}")
    print(f"Summary: Trades={total_trades} | Net R={net_r:.2f}R | WR={win_rate:.1f}% | PF={profit_factor:.2f} | Exp={expectancy:.2f}R | MaxDD={max_dd_r:.2f}R")


if __name__ == "__main__":
    run_full_dev_matrix()
