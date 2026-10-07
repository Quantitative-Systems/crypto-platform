"""Canonical Multi-Timeframe Research Matrix Runner.

Executes the strategy-agnostic Market Model across the 4 fixed timeframe sets:
- SET 1: 1M -> 1W -> 1D
- SET 2: 1W -> 1D -> 4H
- SET 3: 1D -> 4H -> 1H (Vertical Slice)
- SET 4: 4H -> 1H -> 15M

Across assets: BTCUSDT, ETHUSDT, SOLUSDT
Under both hypotheses:
- HYP_A_PULLBACK (Ride HTF Pullback)
- HYP_B_CONTINUATION (Ride HTF Continuation)

Enforces:
- Minimum Target: >= 4.0R floor (< 4R = REJECT)
- Account Risk: 1.0% per trade
- Causal execution: zero lookahead, next-bar open fill, adverse-first collision
- MTF monotonic structural trailing stop
- HTF TP destination
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine, StreamMetrics, TradeRecord
from research.experiments.mtf_strategy_coordinator import MTFStrategyCoordinator

CACHE_DIR = WORKSPACE_ROOT / "market_data" / "cache"
RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "CANONICAL_MTF_BASELINE"

# Timeframe Set Definitions
TIMEFRAME_SETS = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"},
}

HYPOTHESES = ["HYP_A_PULLBACK", "HYP_B_CONTINUATION"]

# Split timestamps (UTC ms)
# DEV: Start to 2022-12-31 23:59:59
# VAL: 2023-01-01 to 2024-06-30 23:59:59
# OOS: 2024-07-01 to End
DEV_END_MS = int(datetime(2022, 12, 31, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)
VAL_END_MS = int(datetime(2024, 6, 30, 23, 59, 59, tzinfo=timezone.utc).timestamp() * 1000)


def load_series_arrays(symbol: str, timeframe: str) -> Optional[Dict[str, np.ndarray]]:
    clean = symbol.replace("/", "").replace("-", "").upper()
    cache_path = CACHE_DIR / f"binance_{clean}_{timeframe}.json"
    if not cache_path.exists():
        print(f"[WARN] Missing cache file: {cache_path}")
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to read {cache_path}: {e}")
        return None

    if not raw or len(raw) < 20:
        print(f"[WARN] Insufficient data in {cache_path}: {len(raw) if raw else 0} bars")
        return None

    raw.sort(key=lambda x: x[0])
    ts = np.array([int(b[0]) for b in raw], dtype=np.int64)
    o = np.array([float(b[1]) for b in raw], dtype=float)
    h = np.array([float(b[2]) for b in raw], dtype=float)
    l = np.array([float(b[3]) for b in raw], dtype=float)
    c = np.array([float(b[4]) for b in raw], dtype=float)
    v = np.array([float(b[5]) for b in raw], dtype=float)
    # If close_time element [6] is missing, estimate as ts + interval
    if len(raw[0]) > 6:
        close_ts = np.array([int(b[6]) for b in raw], dtype=np.int64)
    else:
        diff = int(ts[1] - ts[0]) if len(ts) > 1 else 3600000
        close_ts = ts + diff - 1

    return {
        "ts": ts,
        "o": o,
        "h": h,
        "l": l,
        "c": c,
        "v": v,
        "close_ts": close_ts,
    }


def split_trades(trades: List[TradeRecord]) -> Dict[str, List[TradeRecord]]:
    dev = [t for t in trades if t.entry_ts <= DEV_END_MS]
    val = [t for t in trades if DEV_END_MS < t.entry_ts <= VAL_END_MS]
    oos = [t for t in trades if t.entry_ts > VAL_END_MS]
    return {"FULL": trades, "DEV": dev, "VAL": val, "OOS": oos}


def compute_metrics_for_trades(
    trades: List[TradeRecord], stream_id: str, symbol: str, timeframe_set: str, hypothesis: str
) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "expectancy_r": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
            "average_r": 0.0,
            "median_r": 0.0,
            "largest_win_r": 0.0,
            "largest_loss_r": 0.0,
            "target_4r_hit_rate": 0.0,
            "avg_bars_held": 0.0,
        }

    rs = np.array([t.realized_r for t in trades], dtype=float)
    wins = rs[rs > 0]
    losses = rs[rs < 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / n
    loss_rate = loss_count / n
    total_r = float(np.sum(rs))
    exp_r = float(np.mean(rs))

    gross_win = float(np.sum(wins)) if win_count > 0 else 0.0
    gross_loss = abs(float(np.sum(losses))) if loss_count > 0 else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (99.0 if gross_win > 0 else 0.0)

    cum_r = np.cumsum(rs)
    peak = np.maximum.accumulate(cum_r)
    max_dd = float(np.max(peak - cum_r)) if len(cum_r) else 0.0

    target_4r_hits = sum(1 for t in trades if t.exit_reason == "HTF_TP" and t.realized_r >= 3.8)
    target_4r_hit_rate = target_4r_hits / n

    bars = [t.bars_held for t in trades]
    avg_bars = float(np.mean(bars)) if len(bars) else 0.0

    return {
        "total_trades": n,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round(win_rate, 4),
        "loss_rate": round(loss_rate, 4),
        "expectancy_r": round(exp_r, 4),
        "total_r": round(total_r, 2),
        "profit_factor": round(min(pf, 99.0), 3),
        "max_drawdown_r": round(max_dd, 2),
        "average_r": round(exp_r, 4),
        "median_r": round(float(np.median(rs)), 4),
        "largest_win_r": round(float(np.max(rs)), 2),
        "largest_loss_r": round(float(np.min(rs)), 2),
        "target_4r_hit_rate": round(target_4r_hit_rate, 4),
        "avg_bars_held": round(avg_bars, 1),
    }


def run_experiment_stream(
    symbol: str,
    set_name: str,
    hypothesis: str,
    min_target_r: float = 4.0,
) -> Optional[Dict[str, Any]]:
    tf_cfg = TIMEFRAME_SETS[set_name]
    htf_tf = tf_cfg["htf"]
    mtf_tf = tf_cfg["mtf"]
    ltf_tf = tf_cfg["ltf"]

    htf_data = load_series_arrays(symbol, htf_tf)
    mtf_data = load_series_arrays(symbol, mtf_tf)
    ltf_data = load_series_arrays(symbol, ltf_tf)

    if htf_data is None or mtf_data is None or ltf_data is None:
        print(f"[SKIP] Incomplete series for {symbol} {set_name}")
        return None

    stream_id = f"{symbol[:3]}_{set_name}_{hypothesis}"
    hyp_type = "PULLBACK" if "PULLBACK" in hypothesis else "CONTINUATION"

    print(f"\n[RUN] Executing stream: {stream_id}")
    print(f"      Timeframes: HTF={htf_tf} ({len(htf_data['c'])}), MTF={mtf_tf} ({len(mtf_data['c'])}), LTF={ltf_tf} ({len(ltf_data['c'])})")

    t0 = time.time()
    coordinator = MTFStrategyCoordinator(
        timeframe_set_id=set_name,
        htf_label=htf_tf,
        mtf_label=mtf_tf,
        ltf_label=ltf_tf,
        hypothesis_type=hyp_type,
        min_target_r=min_target_r,
    )

    candidates, mtf_trailing_map = coordinator.scan_signals(
        symbol=symbol,
        htf_data=htf_data,
        mtf_data=mtf_data,
        ltf_data=ltf_data,
    )

    engine = CausalBacktestEngine(
        taker_fee_bps=5.0,
        slippage_bps=2.0,
        min_target_r=min_target_r,
    )

    metrics = engine.execute_stream(
        stream_id=stream_id,
        symbol=symbol,
        timeframe_set=set_name,
        hypothesis=hypothesis,
        ltf_opens=ltf_data["o"],
        ltf_highs=ltf_data["h"],
        ltf_lows=ltf_data["l"],
        ltf_closes=ltf_data["c"],
        ltf_timestamps=ltf_data["ts"],
        signal_candidates=candidates,
        mtf_trailing_levels=mtf_trailing_map,
    )

    elapsed = round(time.time() - t0, 2)
    splits = split_trades(metrics.trades)
    split_metrics = {
        name: compute_metrics_for_trades(t_list, stream_id, symbol, set_name, hypothesis)
        for name, t_list in splits.items()
    }

    print(f"      Finished in {elapsed}s | Signals: {len(candidates)} | Executed Trades: {metrics.total_trades}")
    print(f"      FULL: Trades={metrics.total_trades}, Total R={metrics.total_r:.2f}, Exp R={metrics.expectancy_r:.3f}, PF={metrics.profit_factor:.2f}")
    print(f"      DEV : Trades={split_metrics['DEV']['total_trades']}, Total R={split_metrics['DEV']['total_r']:.2f}")
    print(f"      VAL : Trades={split_metrics['VAL']['total_trades']}, Total R={split_metrics['VAL']['total_r']:.2f}")
    print(f"      OOS : Trades={split_metrics['OOS']['total_trades']}, Total R={split_metrics['OOS']['total_r']:.2f}")

    stream_artifact = {
        "stream_id": stream_id,
        "symbol": symbol,
        "timeframe_set": set_name,
        "hypothesis": hypothesis,
        "min_target_r": min_target_r,
        "elapsed_sec": elapsed,
        "signal_candidate_count": len(candidates),
        "full_metrics": metrics.summary_dict(),
        "splits": split_metrics,
        "trades": [
            {
                "entry_ts": t.entry_ts,
                "exit_ts": t.exit_ts,
                "direction": t.direction,
                "entry_px": t.entry_px,
                "exit_px": t.exit_px,
                "initial_sl": t.initial_sl,
                "target_px": t.target_px,
                "target_r": t.target_r,
                "realized_r": t.realized_r,
                "exit_reason": t.exit_reason,
                "bars_held": t.bars_held,
            }
            for t in metrics.trades
        ],
    }

    return stream_artifact


def main():
    parser = argparse.ArgumentParser(description="Run MTF Baseline Research Experiments")
    parser.add_argument("--assets", nargs="+", default=["BTCUSDT", "ETHUSDT", "SOLUSDT"], help="Assets to test")
    parser.add_argument("--sets", nargs="+", default=["SET_1", "SET_2", "SET_3", "SET_4"], help="Timeframe sets")
    parser.add_argument("--hypotheses", nargs="+", default=HYPOTHESES, help="Hypotheses to test")
    parser.add_argument("--min_r", type=float, default=4.0, help="Minimum Target R floor")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_results: Dict[str, Any] = {}

    print("=" * 70)
    print("STARTING CANONICAL MTF RESEARCH EXPERIMENTS")
    print(f"Assets: {args.assets}")
    print(f"Timeframe Sets: {args.sets}")
    print(f"Hypotheses: {args.hypotheses}")
    print(f"Minimum Target R: {args.min_r}")
    print("=" * 70)

    for asset in args.assets:
        for tf_set in args.sets:
            for hyp in args.hypotheses:
                res = run_experiment_stream(asset, tf_set, hyp, min_target_r=args.min_r)
                if res is not None:
                    stream_id = res["stream_id"]
                    all_results[stream_id] = res

                    # Save individual stream JSON
                    out_path = RESULTS_DIR / f"{stream_id}.json"
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(res, f, indent=2)

    # Save MASTER SUMMARY
    summary_path = RESULTS_DIR / "MASTER_SUMMARY.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "min_target_r": args.min_r,
                "total_streams": len(all_results),
                "streams": {k: {"full": v["full_metrics"], "splits": v["splits"]} for k, v in all_results.items()},
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 70)
    print("ALL EXPERIMENTS COMPLETED!")
    print(f"Total streams executed: {len(all_results)}")
    print(f"Master summary saved to: {summary_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
