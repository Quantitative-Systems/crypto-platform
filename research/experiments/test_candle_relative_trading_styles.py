"""Empirical Research Experiment: Candle-Relative Trading Styles across All 5 Sets.

Tests the user's profound hypothesis:
"Trading styles (Scalping, Intraday, Swing, Positional, Investing) are defined by 
CANDLE GEOMETRY (reaction size and duration), NOT by clock time.
Can scalping or intraday styles work on Set 1 (1M->1w->1d)?
Can swing or positional styles work on lower sets?"

Styles Tested:
1. SCALP: Target 2.0R | Quick BE @ 1.0R | Max 15 bars
2. INTRADAY_MOMENTUM: Target 3.0R | BE @ 1.2R | Max 40 bars
3. SWING: Target 4.5R | BE @ 1.5R | MTF Trailing | Max 150 bars
4. POSITIONAL: Target 7.0R | BE @ 2.0R | MTF Trailing | Max 300 bars
5. INVESTING: Target 10.0R | BE @ 2.5R | MTF Trailing | Max 1000 bars
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

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "STYLE_DIVERSITY_RESEARCH"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


STYLES = {
    "SCALP": {
        "target_r": 2.0,
        "be_threshold_r": 1.0,
        "max_holding_bars": 15,
        "description": "Quick reaction capture (1-15 bars)"
    },
    "INTRADAY": {
        "target_r": 3.0,
        "be_threshold_r": 1.2,
        "max_holding_bars": 40,
        "description": "Impulse momentum wave (10-40 bars)"
    },
    "SWING": {
        "target_r": 4.5,
        "be_threshold_r": 1.5,
        "max_holding_bars": 150,
        "description": "Multi-leg wave expansion (30-150 bars)"
    },
    "POSITIONAL": {
        "target_r": 7.0,
        "be_threshold_r": 2.0,
        "max_holding_bars": 300,
        "description": "Full dealing range expansion (50-300 bars)"
    },
    "INVESTING": {
        "target_r": 10.0,
        "be_threshold_r": 2.5,
        "max_holding_bars": 1000,
        "description": "Macro cycle structural trend (100-1000 bars)"
    },
}


def load_all_7_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_style_experiment():
    print("=" * 110)
    print("RESEARCH EXPERIMENT: TESTING CANDLE-RELATIVE STYLES ACROSS ALL 5 SETS")
    print("=" * 110)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    sets = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

    coordinator = CascadingFractalCoordinator(
        min_target_r=1.5,  # Allow signals down to 1.5R for scalp analysis
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )

    style_matrix_results: Dict[str, Dict[str, Any]] = {
        style_name: {s: {"trades": 0, "wins": 0, "net_r": 0.0, "gross_profit": 0.0, "gross_loss": 0.0} for s in sets}
        for style_name in STYLES
    }

    total_evals = 0

    for asset in assets:
        all_data = load_all_7_timeframes(asset)
        if len(all_data) < 3:
            continue

        print(f"\nProcessing Asset: {asset}...")

        for target_set in sets:
            cfg = coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]
            if ltf_tf not in all_data:
                continue

            ltf_data = all_data[ltf_tf]

            # Scan signals once for this set
            raw_candidates, trailing_map = coordinator.scan_cascading_candidates(
                symbol=asset,
                target_set=target_set,
                all_data=all_data,
            )

            if not raw_candidates:
                continue

            # Now test EACH style on these exact same candidate locations!
            for style_name, style_cfg in STYLES.items():
                style_target_r = style_cfg["target_r"]
                max_bars = style_cfg["max_holding_bars"]

                # Adapt candidate targets to this style
                adapted_candidates = []
                for c in raw_candidates:
                    cand = dict(c) if isinstance(c, dict) else c.__dict__.copy()
                    dir_val = cand["direction"]
                    entry = cand["entry_price"]
                    sl = cand["stop_price"]
                    risk = abs(entry - sl)

                    # Set style-specific target price
                    if dir_val == 1:
                        target = entry + (risk * style_target_r)
                    else:
                        target = entry - (risk * style_target_r)

                    cand["target_price"] = target
                    cand["target_r"] = style_target_r
                    adapted_candidates.append(cand)

                # Execute causal backtest with style parameters
                engine = CausalBacktestEngine(
                    taker_fee_bps=5.0,
                    slippage_bps=2.0,
                    min_target_r=style_target_r,
                    max_holding_bars=max_bars,
                )

                stream_id = f"{asset[:3]}_{target_set}_{style_name}"
                metrics = engine.execute_stream(
                    stream_id=stream_id,
                    symbol=asset,
                    timeframe_set=target_set,
                    hypothesis=f"STYLE_{style_name}",
                    ltf_opens=ltf_data["o"],
                    ltf_highs=ltf_data["h"],
                    ltf_lows=ltf_data["l"],
                    ltf_closes=ltf_data["c"],
                    ltf_timestamps=ltf_data["ts"],
                    signal_candidates=adapted_candidates,
                    mtf_trailing_levels=trailing_map,
                )

                # Aggregate into matrix
                slot = style_matrix_results[style_name][target_set]
                slot["trades"] += metrics.total_trades
                slot["wins"] += metrics.win_count
                slot["net_r"] += metrics.total_r
                for t in metrics.trades:
                    if t.realized_r > 0:
                        slot["gross_profit"] += t.realized_r
                    else:
                        slot["gross_loss"] += abs(t.realized_r)
                total_evals += metrics.total_trades

    # Print Final Style-by-Set Performance Grid
    print("\n" + "=" * 110)
    print("CANDLE-RELATIVE STYLE MATRIX RESULTS (ACROSS BTC, ETH, SOL, BNB)")
    print("=" * 110)

    header = f"{'STYLE':<12} | {'SET_1 (Macro)':<18} | {'SET_2 (Swing)':<18} | {'SET_3 (Intraday)':<18} | {'SET_4 (Scalp)':<18} | {'SET_5 (Micro)':<18} | {'TOTAL ALPHA':<12}"
    print(header)
    print("-" * 110)

    summary_export = {}

    for style_name, set_dict in style_matrix_results.items():
        row_str = f"{style_name:<12} | "
        style_total_r = 0.0
        style_total_trades = 0
        style_total_profit = 0.0
        style_total_loss = 0.0

        for target_set in sets:
            st = set_dict[target_set]
            n = st["trades"]
            net_r = st["net_r"]
            wr = (st["wins"] / n * 100) if n > 0 else 0.0
            pf = (st["gross_profit"] / st["gross_loss"]) if st["gross_loss"] > 0 else (99.0 if st["gross_profit"] > 0 else 0.0)

            style_total_r += net_r
            style_total_trades += n
            style_total_profit += st["gross_profit"]
            style_total_loss += st["gross_loss"]

            cell = f"{net_r:+.1f}R (N={n}, {wr:.0f}%)" if n > 0 else "0.0R (N=0)"
            row_str += f"{cell:<18} | "

        tot_pf = (style_total_profit / style_total_loss) if style_total_loss > 0 else 0.0
        row_str += f"{style_total_r:+.1f}R (PF {tot_pf:.2f})"
        print(row_str)

        summary_export[style_name] = {
            "total_trades": style_total_trades,
            "total_net_r": round(style_total_r, 2),
            "profit_factor": round(tot_pf, 2),
            "by_set": {s: {"trades": set_dict[s]["trades"], "net_r": round(set_dict[s]["net_r"], 2)} for s in sets}
        }

    print("=" * 110)

    # Save artifact
    out_file = RESULTS_DIR / "style_matrix_validation.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_export, f, indent=2)

    print(f"\nArtifact successfully saved to: {out_file}")


if __name__ == "__main__":
    run_style_experiment()
