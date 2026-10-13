"""Institutional Cascading Fractal Backtest Runner.

Executes the unified top-down cascading multi-timeframe strategy across
all 4 crypto pairs (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT) and all 5 timeframe sets:

    Set 1: 1M -> 1w -> 1d
    Set 2: 1w -> 1d -> 4h
    Set 3: 1d -> 4h -> 1h
    Set 4: 4h -> 1h -> 15m (Permission-gated by Macro Baton)
    Set 5: 1h -> 15m -> 3m (Permission-gated by Macro Baton)

Outputs are saved in: research/results/CASCADING_FRACTAL_RESULTS/
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays
RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "CASCADING_FRACTAL_RESULTS"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_all_7_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def main():
    print("=" * 100)
    print("INSTITUTIONAL CASCADING FRACTAL BACKTEST RUNNER")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("Enforcing Top-Down Macro Baton Transmission, 1% Risk Sizing, and Minimum 4R Floor")
    print("=" * 100)

    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

    coordinator = CascadingFractalCoordinator(
        min_target_r=4.0,
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )

    engine = CausalBacktestEngine(
        taker_fee_bps=5.0,
        slippage_bps=2.0,
        min_target_r=4.0,
        max_holding_bars=200,
    )

    all_stream_metrics: Dict[str, Any] = {}
    all_trades: List[Dict[str, Any]] = []

    for asset in assets:
        print(f"\n[{asset}] Loading 7-timeframe series...")
        all_data = load_all_7_timeframes(asset)
        available_tfs = list(all_data.keys())
        print(f"[{asset}] Available timeframes: {available_tfs}")

        for target_set in sets:
            stream_id = f"CASCADE_{asset[:3]}_{target_set}"
            cfg = coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]

            if ltf_tf not in all_data:
                continue

            ltf_data = all_data[ltf_tf]

            t0 = time.time()
            candidates, trailing_map = coordinator.scan_cascading_candidates(
                symbol=asset,
                target_set=target_set,
                all_data=all_data,
            )
            scan_time = time.time() - t0

            if not candidates:
                print(f"  [{stream_id:<32}] N=   0 | No aligned signals | {scan_time:.2f}s")
                continue

            # Execute causal backtest stream
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

            all_stream_metrics[stream_id] = metrics.summary_dict()
            for t in metrics.trades:
                all_trades.append({
                    "symbol": t.symbol,
                    "stream_id": t.stream_id,
                    "direction": t.direction,
                    "entry_ts": t.entry_ts,
                    "exit_ts": t.exit_ts,
                    "entry_px": t.entry_px,
                    "exit_px": t.exit_px,
                    "realized_r": t.realized_r,
                    "exit_reason": t.exit_reason,
                    "bars_held": t.bars_held,
                })

            summary = metrics.summary_dict()
            print(
                f"  [{stream_id:<32}] N={summary['total_trades']:>4} | "
                f"WR={summary['win_rate']*100:>5.1f}% | "
                f"ExpR={summary['expectancy_r']:>7.4f} | "
                f"TotR={summary['total_r']:>8.2f} | "
                f"PF={summary['profit_factor']:>6.3f} | {scan_time:.2f}s",
                flush=True,
            )

    # Compile master results
    total_trades = len(all_trades)
    net_r = sum(t["realized_r"] for t in all_trades)
    wins = [t for t in all_trades if t["realized_r"] > 0]
    losses = [t for t in all_trades if t["realized_r"] <= 0]
    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
    gross_win_r = sum(t["realized_r"] for t in wins)
    gross_loss_r = abs(sum(t["realized_r"] for t in losses))
    pf = gross_win_r / gross_loss_r if gross_loss_r > 0 else 0.0

    master_summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "total_r": round(net_r, 2),
        "profit_factor": round(pf, 3),
        "expectancy_r": round(net_r / total_trades, 4) if total_trades > 0 else 0.0,
        "streams": all_stream_metrics,
        "trades": all_trades,
    }

    out_file = RESULTS_DIR / "master_cascading_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(master_summary, f, indent=2)

    print("\n" + "=" * 100)
    print("CASCADING FRACTAL BACKTEST SUMMARY:")
    print(f"Total Causal Trades : {total_trades}")
    print(f"Win Rate            : {win_rate*100:.1f}%")
    print(f"Net Realized Return : {net_r:+.2f} R")
    print(f"Profit Factor       : {pf:.3f}")
    print(f"Expectancy Per Trade: {net_r/max(total_trades,1):+.4f} R")
    print(f"Results Saved To    : {out_file}")
    print("=" * 100)


if __name__ == "__main__":
    main()
