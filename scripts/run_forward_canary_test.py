"""Institutional Forward Canary Execution Test Driver.

Simulates live forward-walk execution across top crypto assets:
- Evaluates bar-by-bar causal tick arrivals (zero lookahead).
- Enforces Prime Custody Firewall (80% Cold / 20% Hot).
- Routes orders through Smart Execution Gateway (Maker-Rebate optimization).
- Tracks open positions, +1.5R Break-Even locks, and MTF trailing stops.
- Streams real-time fills into FORWARD_CANARY_LEDGER.jsonl and generates
  the audited track record in FORWARD_CANARY_TRACK_RECORD.json.
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

from execution.shadow.forward_canary_runner import ForwardCanaryRunner
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

CANARY_ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "ARBUSDT", "INJUSDT", "RENDERUSDT", "NEARUSDT"
]

CANARY_SETS = ["SET_2", "SET_3"]
TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]


def load_all_series(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in TIMEFRAMES:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_forward_canary_soak_test():
    print("=" * 105, flush=True)
    print("   INSTITUTIONAL LIVE FORWARD PAPER & CANARY SOAK TEST RUNNER", flush=True)
    print("   Custody: 80% Cold Vault / 20% Hot | Smart Execution: Maker Rebates (-0.5 bps) | >= 4.0R TP", flush=True)
    print("   Assets: " + ", ".join(CANARY_ASSETS), flush=True)
    print("=" * 105, flush=True)

    runner = ForwardCanaryRunner(
        symbols=CANARY_ASSETS,
        total_fund_equity_usd=100_000.0,
        risk_per_trade_pct=0.01,
        max_portfolio_heat_pct=0.03,
        min_target_r=4.0,
        max_hot_collateral_pct=0.20,
    )

    total_eval_bars = 100

    print(f"\n[1/3] Simulating Forward Live Market Ticks across last {total_eval_bars} bars...", flush=True)

    # Preload data
    asset_data = {}
    for sym in CANARY_ASSETS:
        d = load_all_series(sym)
        if len(d) >= 4:
            asset_data[sym] = d

    # Walk forward across time bars
    for sym, all_data in asset_data.items():
        for target_set in CANARY_SETS:
            cfg = runner.coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]
            if ltf_tf not in all_data:
                continue

            ltf_data = all_data[ltf_tf]
            n_bars = len(ltf_data["c"])
            if n_bars < total_eval_bars + 30:
                continue

            start_idx = n_bars - total_eval_bars

            # Causal walk forward in time
            for i in range(start_idx, n_bars):
                # Build causal slices up to bar i
                causal_sliced = {}
                t_curr = int(ltf_data["ts"][i])
                curr_c = float(ltf_data["c"][i])
                curr_h = float(ltf_data["h"][i])
                curr_l = float(ltf_data["l"][i])

                for tf, s in all_data.items():
                    s_idx = np.searchsorted(s["close_ts"], t_curr, side="right") - 1
                    if s_idx >= 5:
                        causal_sliced[tf] = {
                            "o": s["o"][:s_idx + 1],
                            "h": s["h"][:s_idx + 1],
                            "l": s["l"][:s_idx + 1],
                            "c": s["c"][:s_idx + 1],
                            "v": s["v"][:s_idx + 1],
                            "ts": s["ts"][:s_idx + 1],
                            "close_ts": s["close_ts"][:s_idx + 1],
                        }

                if len(causal_sliced) < 3:
                    continue

                # 1. Update existing open positions
                runner.update_open_positions(
                    symbol=sym,
                    current_high=curr_h,
                    current_low=curr_l,
                    current_close=curr_c,
                )

                # 2. Evaluate new candidate signals
                spread = curr_c * 0.0002  # Realistic 2 bps spread
                bid = curr_c - (spread / 2.0)
                ask = curr_c + (spread / 2.0)

                runner.evaluate_live_market_tick(
                    symbol=sym,
                    target_set=target_set,
                    all_data=causal_sliced,
                    current_bid=bid,
                    current_ask=ask,
                )

    # Generate and persist summary
    summary = runner.persist_track_record_summary()

    print("\n" + "=" * 105, flush=True)
    print("   INSTITUTIONAL FORWARD CANARY AUDIT REPORT", flush=True)
    print("=" * 105, flush=True)
    perf = summary["performance_metrics"]
    custody = summary["custody_architecture"]
    exec_m = summary["smart_execution_metrics"]

    print(f"Total Closed Trades           : {perf['total_closed_trades']}")
    print(f"Active Open Positions         : {perf['active_open_trades']}")
    print(f"Forward Win Rate              : {perf['win_rate_pct']:.1f}%")
    print(f"Net Realized Alpha            : {perf['net_realized_r']:+.2f}R")
    print(f"Forward Profit Factor         : {perf['profit_factor']:.2f}")
    print(f"Forward Expectancy per Trade  : {perf['expectancy_r']:+.3f}R")
    print("-" * 105, flush=True)
    print(f"Custody Model                 : {custody['provider']} (80/20 Rule Compliant: {custody['is_within_budget']})")
    print(f"Cold Vault Equity             : ${custody['cold_vault_usd']:,.2f} ({100 - custody['hot_exchange_pct']:.1f}%)")
    print(f"Hot Exchange Margin           : ${custody['hot_exchange_usd']:,.2f} ({custody['hot_exchange_pct']:.1f}%)")
    print("-" * 105, flush=True)
    print(f"Total Orders Routed           : {exec_m['total_routed_orders']}")
    print(f"Maker Orders (Rebate Captured): {exec_m['maker_orders_count']} ({exec_m['maker_orders_count'] / max(exec_m['total_routed_orders'], 1) * 100:.1f}%)")
    print(f"Total Fees Earned/Paid        : ${exec_m['total_fees_usd']:,.2f}")
    print(f"Average Execution Slippage    : {exec_m['avg_slippage_bps']:.2f} bps")
    print("=" * 105, flush=True)
    print(f"\n[Artifact Persisted]: {runner.track_record_file}")
    print(f"[Ledger Persisted]  : {runner.ledger_file}")


if __name__ == "__main__":
    run_forward_canary_soak_test()
