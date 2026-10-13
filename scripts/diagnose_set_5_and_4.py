"""Forensic Diagnostic on Set 5 (1h -> 15m -> 3m) and Set 4 (4h -> 1h -> 15m).

Answers the exact questions:
1. Why does Set 5 lose while Sets 1, 2, 3 are highly profitable?
2. Is it exchange friction (fee + slippage), noise / false breakouts, or stop distance?
3. What happens if friction is 0 vs real?
4. How do Sets 4 and 5 perform across all available assets individually?
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays


ALL_ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
    "LINKUSDT", "NEARUSDT", "SUIUSDT", "DOTUSDT"
]

TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]


def load_all_7_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in TIMEFRAMES:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_set_diagnostics(target_set: str, fee_bps: float = 5.0, slip_bps: float = 2.0) -> Dict[str, Any]:
    coordinator = CascadingFractalCoordinator(min_target_r=4.0)
    engine = CausalBacktestEngine(
        taker_fee_bps=fee_bps,
        slippage_bps=slip_bps,
        min_target_r=4.0,
        max_holding_bars=200,
    )

    all_trades = []
    asset_results = {}

    for asset in ALL_ASSETS:
        all_data = load_all_7_timeframes(asset)
        cfg = coordinator.TIMEFRAME_SETS[target_set]
        ltf_tf = cfg["ltf"]

        if ltf_tf not in all_data or cfg["htf"] not in all_data or cfg["mtf"] not in all_data:
            continue

        ltf_data = all_data[ltf_tf]
        candidates, trailing_map = coordinator.scan_cascading_candidates(
            symbol=asset,
            target_set=target_set,
            all_data=all_data,
        )

        if not candidates:
            asset_results[asset] = {"n": 0, "net_r": 0.0, "wr": 0.0, "pf": 0.0}
            continue

        stream_id = f"DIAG_{asset}_{target_set}"
        metrics = engine.execute_stream(
            stream_id=stream_id,
            symbol=asset,
            timeframe_set=target_set,
            hypothesis="CASCADING_BATON",
            ltf_opens=ltf_data["o"],
            ltf_highs=ltf_data["h"],
            ltf_lows=ltf_data["l"],
            ltf_closes=ltf_data["c"],
            ltf_timestamps=ltf_data["ts"],
            signal_candidates=candidates,
            mtf_trailing_levels=trailing_map,
        )

        for t in metrics.trades:
            # Find candidate info
            stop_dist_pct = abs(t.entry_px - t.initial_risk_dist) / t.entry_px * 100
            friction_pct = (fee_bps * 2.0 + slip_bps * 2.0) / 100.0  # total friction in %
            all_trades.append({
                "asset": asset,
                "set": target_set,
                "realized_r": t.realized_r,
                "exit_reason": t.exit_reason,
                "bars_held": t.bars_held,
                "mfe_r": t.mfe_r,
                "mae_r": t.mae_r,
                "risk_dist": t.initial_risk_dist,
                "risk_dist_pct": stop_dist_pct,
            })

        asset_results[asset] = {
            "n": metrics.total_trades,
            "net_r": round(metrics.total_r, 2),
            "wr": round(metrics.win_rate * 100, 1),
            "pf": round(metrics.profit_factor, 2),
        }

    total_n = len(all_trades)
    net_r = sum(t["realized_r"] for t in all_trades)
    wins = [t for t in all_trades if t["realized_r"] > 0]
    losses = [t for t in all_trades if t["realized_r"] <= 0]
    wr = len(wins) / max(total_n, 1) * 100
    pf = sum(t["realized_r"] for t in wins) / max(abs(sum(t["realized_r"] for t in losses)), 0.001)

    avg_bars = np.mean([t["bars_held"] for t in all_trades]) if all_trades else 0
    avg_mfe = np.mean([t["mfe_r"] for t in all_trades]) if all_trades else 0
    avg_mae = np.mean([t["mae_r"] for t in all_trades]) if all_trades else 0
    avg_risk_dist_pct = np.mean([t["risk_dist_pct"] for t in all_trades]) if all_trades else 0

    reasons = {}
    for t in all_trades:
        reasons[t["exit_reason"]] = reasons.get(t["exit_reason"], 0) + 1

    return {
        "set": target_set,
        "fee_bps": fee_bps,
        "slip_bps": slip_bps,
        "total_trades": total_n,
        "net_r": round(net_r, 2),
        "win_rate": round(wr, 1),
        "profit_factor": round(pf, 2),
        "avg_bars_held": round(float(avg_bars), 1),
        "avg_mfe_r": round(float(avg_mfe), 2),
        "avg_mae_r": round(float(avg_mae), 2),
        "avg_risk_dist_pct": round(float(avg_risk_dist_pct), 3),
        "exit_reasons": reasons,
        "asset_results": asset_results,
    }


def main():
    print("=" * 100, flush=True)
    print("FORENSIC DIAGNOSTIC SUITE: WHY IS SET 5 LOSING?", flush=True)
    print("=" * 100, flush=True)

    # 1. Diagnose SET 5 with Real Exchange Friction (5 bps fee, 2 bps slip)
    print("\n[TEST 1] SET 5 (1h -> 15m -> 3m) Under Real Friction (10 bps RT fee, 4 bps RT slip)...", flush=True)
    t0 = time.time()
    res_set5_real = run_set_diagnostics("SET_5", fee_bps=5.0, slip_bps=2.0)
    print(f"  -> SET 5 Real completed in {time.time()-t0:.1f}s", flush=True)

    # 2. Diagnose SET 5 with ZERO Friction (0 fee, 0 slip) -> Isolates Market Structure vs Friction
    print("\n[TEST 2] SET 5 (1h -> 15m -> 3m) Under ZERO Friction (Isolating Theoretical Edge)...", flush=True)
    t0 = time.time()
    res_set5_zero = run_set_diagnostics("SET_5", fee_bps=0.0, slip_bps=0.0)
    print(f"  -> SET 5 Zero completed in {time.time()-t0:.1f}s", flush=True)

    # 3. Diagnose SET 4 with Real Exchange Friction
    print("\n[TEST 3] SET 4 (4h -> 1h -> 15m) Under Real Friction...", flush=True)
    t0 = time.time()
    res_set4_real = run_set_diagnostics("SET_4", fee_bps=5.0, slip_bps=2.0)
    print(f"  -> SET 4 Real completed in {time.time()-t0:.1f}s", flush=True)

    # Stored benchmark for SET 3 from certified run
    res_set3_real = {
        "total_trades": 1883,
        "win_rate": 27.7,
        "net_r": 295.83,
        "profit_factor": 1.28,
        "avg_risk_dist_pct": 2.450,
        "avg_bars_held": 42.1,
        "avg_mfe_r": 3.82,
    }

    print("\n" + "=" * 100, flush=True)
    print("COMPARATIVE DIAGNOSTIC RESULTS", flush=True)
    print("=" * 100, flush=True)
    print(f"{'Metric':<30} {'SET 5 (Real)':<16} {'SET 5 (Zero Fric)':<18} {'SET 4 (Real)':<16} {'SET 3 (Benchmark)':<16}")
    print("-" * 100)
    print(f"{'Total Trades':<30} {res_set5_real['total_trades']:<16} {res_set5_zero['total_trades']:<18} {res_set4_real['total_trades']:<16} {res_set3_real['total_trades']:<16}")
    print(f"{'Win Rate':<30} {res_set5_real['win_rate']:>5.1f}%{'':<10} {res_set5_zero['win_rate']:>5.1f}%{'':<12} {res_set4_real['win_rate']:>5.1f}%{'':<10} {res_set3_real['win_rate']:>5.1f}%")
    print(f"{'Net Realized Return':<30} {res_set5_real['net_r']:>+7.2f}R{'':<8} {res_set5_zero['net_r']:>+7.2f}R{'':<10} {res_set4_real['net_r']:>+7.2f}R{'':<8} {res_set3_real['net_r']:>+7.2f}R")
    print(f"{'Profit Factor':<30} {res_set5_real['profit_factor']:>6.2f}{'':<10} {res_set5_zero['profit_factor']:>6.2f}{'':<12} {res_set4_real['profit_factor']:>6.2f}{'':<10} {res_set3_real['profit_factor']:>6.2f}")
    print(f"{'Avg Risk Distance (%)':<30} {res_set5_real['avg_risk_dist_pct']:>6.3f}%{'':<9} {res_set5_zero['avg_risk_dist_pct']:>6.3f}%{'':<11} {res_set4_real['avg_risk_dist_pct']:>6.3f}%{'':<9} {res_set3_real['avg_risk_dist_pct']:>6.3f}%")
    print(f"{'Avg Bars Held':<30} {res_set5_real['avg_bars_held']:>6.1f}{'':<10} {res_set5_zero['avg_bars_held']:>6.1f}{'':<12} {res_set4_real['avg_bars_held']:>6.1f}{'':<10} {res_set3_real['avg_bars_held']:>6.1f}")
    print(f"{'Avg MFE (Max Win Potential)':<30} {res_set5_real['avg_mfe_r']:>6.2f}R{'':<9} {res_set5_zero['avg_mfe_r']:>6.2f}R{'':<11} {res_set4_real['avg_mfe_r']:>6.2f}R{'':<9} {res_set3_real['avg_mfe_r']:>6.2f}R")
    print(f"{'Exit Reasons':<30} {str(res_set5_real['exit_reasons']):<40}")

    print("\n" + "=" * 100)
    print("SET 5 ASSET-BY-ASSET BREAKDOWN:")
    for asset, data in res_set5_real["asset_results"].items():
        print(f"  {asset:<10}: N={data['n']:>3} | WR={data['wr']:>5.1f}% | Net R={data['net_r']:>+7.2f}R | PF={data['pf']:>5.2f}")

    print("\nSET 4 ASSET-BY-ASSET BREAKDOWN:")
    for asset, data in res_set4_real["asset_results"].items():
        print(f"  {asset:<10}: N={data['n']:>3} | WR={data['wr']:>5.1f}% | Net R={data['net_r']:>+7.2f}R | PF={data['pf']:>5.2f}")


if __name__ == "__main__":
    main()
