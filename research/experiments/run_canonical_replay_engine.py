"""
Product 04 — Research Laboratory: Authoritative Canonical Replay Engine
Replays the 15-stream matrix strictly on the 2021-01-01 to 2022-12-31 Development Partition.

Supports two cleanly isolated treatments:
  - H0: Pure unmodified canonical strategy baseline without forward structural expansion
  - ANCHOR_2: Structural forward expansion fallback (1.0x dealing range width)

Zero-leakage, adverse-first collision resolution, zero lookahead protection.
"""

import os
import sys
import json
import time
import argparse
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

sys.path.insert(0, "/home/mrcn2/crypto-platform")

from market_data.warehouse_loader import WarehouseLoader
from market_data.data_certifier import DataCertifier
from research.replayer.causal_replayer import CausalReplayer
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


def run_single_stream(asset: str, tf_set_id: str, treatment: str) -> Dict[str, Any]:
    stream_id = f"{asset}_{tf_set_id}"
    symbol = f"{asset}/USDT"
    tf_info = TF_SET_METADATA[tf_set_id]
    
    t0 = time.time()
    
    # Strictly 2021-01-01 to 2022-12-31 Development Partition
    ltf_start_time_ms = int(datetime(2021, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    end_time_ms = int(datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    period_label = "2021-01-01 to 2022-12-31 (Development Partition)"

    if tf_set_id == "SET_5":
        # 1m/5m public Binance historical depth is limited to 2026 certified cache
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
            "all_candidates": [],
            "engine_runs": {"htf": 0, "mtf": 0, "ltf": 0, "ltf_ticks": 0}
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
        return {
            "stream_id": stream_id,
            "asset": asset,
            "timeframe_set": tf_set_id,
            "error": str(data_err),
            "trades": [],
            "status": "DATA_ERROR",
            "all_candidates": []
        }

    # Configure Replayer
    risk_cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        min_stop_distance_pct=0.001,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False
    )

    enable_expansion = (treatment.upper() in ["ANCHOR_2", "POLARITY_01", "BREAKEVEN_1R", "COMPOSITE_01", "MILESTONE_2_5R"])
    enforce_polarity = (treatment.upper() in ["POLARITY_01", "COMPOSITE_01", "MILESTONE_2_5R"])
    enable_breakeven = (treatment.upper() in ["BREAKEVEN_1R", "COMPOSITE_01", "MILESTONE_2_5R"])
    enable_milestone = (treatment.upper() == "MILESTONE_2_5R")
    target_hierarchy = "STRUCTURAL_OBJECTIVE" if treatment.upper() in ["EXP_TARGET_STRUCTURAL_01", "EXP_TARGET_STRUCTURAL_01_PURE"] else "CLOSEST_OBJECTIVE"
    enable_profit_lock = (treatment.upper() == "PROFIT_LOCK_0.5R_0.25R")
    profit_lock_trigger_r = 0.5 if enable_profit_lock else 1.0
    profit_lock_stop_r = 0.25 if enable_profit_lock else 0.10
    require_htf_kz = (treatment.upper() != "H_MOM_01")

    replayer = CausalReplayer(
        timeframe_set_id=tf_set_id,
        initial_balance=10000.0,
        maker_fee_rate=0.0002,   # 2 bps maker
        taker_fee_rate=0.0005,   # 5 bps taker
        slippage_bps=5.0,        # 5 bps realistic adverse slippage
        enable_mtf_trailing=True, # MTF structural trailing preserved
        enable_profit_lock=enable_profit_lock,
        lockin_r=999.0,
        giveback_r=0.0,
        profit_lock_trigger_r=profit_lock_trigger_r,
        profit_lock_stop_r=profit_lock_stop_r,
        enable_forward_expansion=enable_expansion,
        enforce_displacement_polarity=enforce_polarity,
        enable_breakeven_1r=enable_breakeven,
        enable_milestone_target=enable_milestone,
        milestone_r=2.5,
        target_hierarchy=target_hierarchy,
        require_htf_keyzone=require_htf_kz,
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
    all_candidates = result.get("all_candidates", [])
    elapsed = time.time() - t0

    return {
        "stream_id": stream_id,
        "asset": asset,
        "timeframe_set": tf_set_id,
        "label": tf_info["label"],
        "period": period_label,
        "htf_candles_count": len(htf_candles),
        "mtf_candles_count": len(mtf_candles),
        "ltf_candles_count": len(ltf_candles),
        "execution_time_sec": round(elapsed, 2),
        "trades": closed_trades,
        "all_candidates": all_candidates,
        "status": "COMPLETED",
        "engine_runs": result.get("engine_runs", {})
    }


def compute_aggregate_metrics(all_trades: List[Dict[str, Any]], initial_balance: float = 10000.0) -> Dict[str, Any]:
    total_trades = len(all_trades)
    if total_trades == 0:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "breakevens": 0,
            "win_rate": 0.0, "net_r": 0.0, "gross_r": 0.0, "friction_r": 0.0,
            "expectancy": 0.0, "profit_factor": 0.0, "max_drawdown_r": 0.0,
            "max_consecutive_losses": 0, "avg_mfe_r": 0.0, "median_mfe_r": 0.0,
            "avg_mae_r": 0.0, "median_mae_r": 0.0
        }

    wins = [t for t in all_trades if float(t.get("realized_r", t.get("realized_rr", 0.0))) > 0.0]
    losses = [t for t in all_trades if float(t.get("realized_r", t.get("realized_rr", 0.0))) < 0.0]
    bes = [t for t in all_trades if abs(float(t.get("realized_r", t.get("realized_rr", 0.0)))) < 1e-6]

    net_r_vals = [float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in all_trades]
    gross_r_vals = [float(t.get("gross_r", 0.0)) for t in all_trades]
    
    net_r = sum(net_r_vals)
    gross_r = sum(gross_r_vals)
    friction_r = gross_r - net_r
    expectancy = net_r / total_trades

    win_r_sum = sum(float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in wins)
    loss_r_sum = abs(sum(float(t.get("realized_r", t.get("realized_rr", 0.0))) for t in losses))
    profit_factor = (win_r_sum / loss_r_sum) if loss_r_sum > 0 else (999.0 if win_r_sum > 0 else 0.0)
    win_rate = len(wins) / total_trades * 100.0

    # Drawdown in R
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    for r_val in net_r_vals:
        cum_r += r_val
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd_r:
            max_dd_r = dd

    # Max consecutive losses
    max_consec = 0
    cur_consec = 0
    for r_val in net_r_vals:
        if r_val < 0:
            cur_consec += 1
            if cur_consec > max_consec:
                max_consec = cur_consec
        else:
            cur_consec = 0

    mfe_vals = [float(t.get("mfe_r", 0.0)) for t in all_trades]
    mae_vals = [float(t.get("mae_r", 0.0)) for t in all_trades]

    return {
        "total_trades": total_trades,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(bes),
        "win_rate": round(win_rate, 2),
        "net_r": round(net_r, 4),
        "gross_r": round(gross_r, 4),
        "friction_r": round(friction_r, 4),
        "expectancy": round(expectancy, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown_r": round(max_dd_r, 4),
        "max_consecutive_losses": max_consec,
        "avg_mfe_r": round(float(np.mean(mfe_vals)), 4) if mfe_vals else 0.0,
        "median_mfe_r": round(float(np.median(mfe_vals)), 4) if mfe_vals else 0.0,
        "avg_mae_r": round(float(np.mean(mae_vals)), 4) if mae_vals else 0.0,
        "median_mae_r": round(float(np.median(mae_vals)), 4) if mae_vals else 0.0
    }


def generate_manifest(treatment: str) -> Dict[str, Any]:
    try:
        git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
    except Exception:
        git_commit = "UNKNOWN"
        git_branch = "UNKNOWN"

    config_str = f"treatment={treatment}_balance=10000_maker=0.0002_taker=0.0005_slip=5.0_risk=0.01_rr=4.0_period=2021-2022"
    cfg_hash = hashlib.sha256(config_str.encode()).hexdigest()[:16]

    return {
        "experiment_id": f"CANONICAL_{treatment}_DEV_2021_2022",
        "treatment": treatment,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit,
        "git_branch": git_branch,
        "config_hash": cfg_hash,
        "date_partition": {
            "name": "DEVELOPMENT",
            "start": "2021-01-01T00:00:00Z",
            "end": "2022-12-31T23:59:59Z"
        },
        "universe": {
            "assets": ASSETS,
            "timeframe_sets": TF_SETS,
            "total_streams": 15
        },
        "friction_model": {
            "maker_fee_rate": 0.0002,
            "taker_fee_rate": 0.0005,
            "slippage_bps": 5.0,
            "funding_model": "ZERO_DRIFT_SPOT"
        },
        "risk_model": {
            "max_risk_fraction": 0.01,
            "min_rr_floor": 4.0,
            "min_stop_distance_pct": 0.001
        },
        "execution_model_version": "v1.0.0-causal-adverse-first"
    }


def run_matrix(treatment: str, output_path: str = None, workers: int = 8):
    print("=" * 80)
    print(f"CANONICAL REPLAY ENGINE: TREATMENT = {treatment.upper()}")
    print("Partition: 2021-01-01 to 2022-12-31 (Strict Development Partition)")
    print("Friction: 2 bps maker, 5 bps taker, 5 bps adverse slippage, adverse-first collision")
    print("=" * 80)

    stream_tasks = []
    for tf_set in TF_SETS:
        for asset in ASSETS:
            stream_tasks.append((asset, tf_set))

    results = []
    with ProcessPoolExecutor(max_workers=min(workers, len(stream_tasks))) as executor:
        future_map = {executor.submit(run_single_stream, asset, tf_set, treatment): (asset, tf_set) for asset, tf_set in stream_tasks}
        for future in as_completed(future_map):
            asset, tf_set = future_map[future]
            try:
                res = future.result()
                results.append(res)
                n_trades = len(res.get("trades", []))
                n_cand = len(res.get("all_candidates", []))
                print(f"[{res['stream_id']:10s}] Status: {res['status']:<35s} | Trades: {n_trades:2d} | Candidates: {n_cand:3d} | Time: {res.get('execution_time_sec', 0.0)}s")
            except Exception as e:
                print(f"❌ Error on {asset}_{tf_set}: {e}")

    # Consolidate all trades
    all_trades = []
    for r in results:
        stream_id = r["stream_id"]
        for t in r.get("trades", []):
            t_copy = dict(t)
            t_copy["stream_id"] = stream_id
            all_trades.append(t_copy)

    # Sort trades chronologically
    all_trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)

    aggregate_perf = compute_aggregate_metrics(all_trades)
    manifest = generate_manifest(treatment)

    output_payload = {
        "manifest": manifest,
        "aggregate_performance": aggregate_perf,
        "stream_results": results,
        "all_trades": all_trades
    }

    if output_path is None:
        filename = f"canonical_{treatment.lower()}_dev_results.json"
        output_path = os.path.join("/home/mrcn2/crypto-platform/scratch", filename)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as fp:
        json.dump(output_payload, fp, indent=2)

    print("\n" + "=" * 80)
    print(f"REPLAY COMPLETE: Total Executed Trades = {len(all_trades)} | Net R = {aggregate_perf['net_r']}R | Expectancy = {aggregate_perf['expectancy']}R")
    print(f"Output saved to: {output_path}")
    print("=" * 80)
    return output_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Canonical Replay Engine")
    parser.add_argument("--treatment", type=str, default="H0", choices=["H0", "ANCHOR_2", "POLARITY_01", "BREAKEVEN_1R", "COMPOSITE_01", "MILESTONE_2_5R", "EXP_TARGET_STRUCTURAL_01", "EXP_TARGET_STRUCTURAL_01_PURE", "PROFIT_LOCK_0.5R_0.25R", "H_MOM_01"], help="Experimental treatment")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    parser.add_argument("--workers", type=int, default=8, help="Parallel worker count")
    args = parser.parse_args()

    run_matrix(treatment=args.treatment, output_path=args.output, workers=args.workers)
