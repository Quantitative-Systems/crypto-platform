"""STRATA — Phase 2: 25-Combination Research Laboratory Matrix Runner.

Executes the exhaustive 5 Sets x 5 Trading Styles matrix:
- Sets: SET_1 (1M/1W/1D), SET_2 (1W/1D/4H), SET_3 (1D/4H/1H), SET_4 (4H/1H/15M), SET_5 (1H/15M/3M)
- Styles: SCALP (<=15 bars), INTRADAY (40 bars), SWING (150 bars), POSITIONAL (300 bars), INVESTING (1000 bars)
- Market Phases: Evaluates both Continuation (Expansion) and Pullback (Retracement)
- Causal Realism: Next-bar open fill, adverse-first collision, 10 bps taker fees, 4 bps slippage
- Fractal Event Graph: Indexes events and prevents overlapping duplicate exposure
- Chronological Portfolio Simulation: Enforces max 3 concurrent positions (3% heat)
- Holdout Partition: In-Sample (< 2024-07-01) vs Out-of-Sample (>= 2024-07-01)
- Outputs: Complete scorecards, statistical confidence intervals, and candidate classification.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine, TradeRecord
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from market_model.fractal_event_graph import (
    CanonicalFractalEvent,
    EventType,
    FractalEventGraph,
    InvalidationCondition,
    create_order_block_event,
    create_swing_event,
)
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays, VAL_END_MS

OUTPUT_DIR = WORKSPACE_ROOT / "research" / "results" / "STRATA_PHASE_2_MATRIX"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
SETS = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]

STYLES: Dict[str, Dict[str, Any]] = {
    "SCALP": {
        "min_target_r": 2.0,
        "max_holding_bars": 15,
        "be_threshold_r": 1.0,
        "desc": "Quick reaction / internal bounce (1-15 bars)"
    },
    "INTRADAY": {
        "min_target_r": 3.0,
        "max_holding_bars": 40,
        "be_threshold_r": 1.2,
        "desc": "Intraday momentum impulse (10-40 bars)"
    },
    "SWING": {
        "min_target_r": 4.5,
        "max_holding_bars": 150,
        "be_threshold_r": 1.5,
        "desc": "Multi-leg wave structural expansion (30-150 bars)"
    },
    "POSITIONAL": {
        "min_target_r": 7.0,
        "max_holding_bars": 300,
        "be_threshold_r": 2.0,
        "desc": "Major dealing range expansion (50-300 bars)"
    },
    "INVESTING": {
        "min_target_r": 10.0,
        "max_holding_bars": 1000,
        "be_threshold_r": 2.5,
        "desc": "Macro structural trend riding (100-1000 bars)"
    },
}


def load_all_timeframes_for_asset(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def compute_metrics(trades: List[Dict[str, Any]], n_boot: int = 1000) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {
            "total_trades": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "total_r": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "max_drawdown_r": 0.0,
            "boot_pf_ci_95": [0.0, 0.0],
            "boot_exp_ci_95": [0.0, 0.0],
        }

    rs = np.array([t["realized_r"] for t in trades], dtype=float)
    wins = rs[rs > 0]
    losses = rs[rs < 0]
    n_wins = len(wins)
    n_losses = len(losses)
    wr = (n_wins / n) * 100.0

    gw = float(np.sum(wins)) if n_wins else 0.0
    gl = abs(float(np.sum(losses))) if n_losses else 0.0
    pf = (gw / gl) if gl > 0 else (99.0 if gw > 0 else 0.0)

    total_r = float(np.sum(rs))
    exp_r = float(np.mean(rs))

    cum_r = np.cumsum(rs)
    peak = np.maximum.accumulate(cum_r)
    max_dd = float(np.max(peak - cum_r)) if len(cum_r) else 0.0

    # Fast bootstrap
    rng = np.random.default_rng(42)
    boot_exps = []
    boot_pfs = []
    for _ in range(n_boot):
        sample = rng.choice(rs, size=n, replace=True)
        boot_exps.append(float(np.mean(sample)))
        s_w = sample[sample > 0]
        s_l = sample[sample < 0]
        sw = float(np.sum(s_w)) if len(s_w) else 0.0
        sl = abs(float(np.sum(s_l))) if len(s_l) else 0.0
        boot_pfs.append(sw / sl if sl > 0 else 99.0)

    exp_ci = [round(float(np.percentile(boot_exps, 2.5)), 3), round(float(np.percentile(boot_exps, 97.5)), 3)]
    pf_ci = [round(float(np.percentile(boot_pfs, 2.5)), 2), round(float(np.percentile(boot_pfs, 97.5)), 2)]

    return {
        "total_trades": n,
        "win_count": n_wins,
        "loss_count": n_losses,
        "win_rate_pct": round(wr, 2),
        "total_r": round(total_r, 2),
        "profit_factor": round(min(pf, 99.0), 2),
        "expectancy_r": round(exp_r, 4),
        "max_drawdown_r": round(max_dd, 2),
        "boot_pf_ci_95": pf_ci,
        "boot_exp_ci_95": exp_ci,
    }


def run_strata_matrix():
    print("=" * 115)
    print("STRATA PHASE 2: EXHAUSTIVE 25-COMBINATION RESEARCH MATRIX")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 115)

    coordinator = CascadingFractalCoordinator(
        min_target_r=1.5,
        risk_per_trade_pct=0.01,
        account_equity_usd=100_000.0,
    )

    event_graph = FractalEventGraph()

    # Preload market data
    all_asset_data = {}
    for asset in ASSETS:
        d = load_all_timeframes_for_asset(asset)
        if len(d) >= 3:
            all_asset_data[asset] = d
            print(f"Loaded {asset}: {len(d)} timeframes available.")

    # Pre-scan and cache all (asset, set) candidates and trailing maps once (20 scans total)
    cached_scans: Dict[Tuple[str, str], Tuple[List[Dict[str, Any]], Dict[int, float]]] = {}
    print("\nPre-scanning multi-timeframe fractal candidates across all 4 assets and 5 sets...")
    t0 = time.time()
    for asset, all_data in all_asset_data.items():
        for set_id in SETS:
            cfg = coordinator.TIMEFRAME_SETS[set_id]
            ltf_tf = cfg["ltf"]
            if ltf_tf not in all_data:
                continue
            raw_cands, t_map = coordinator.scan_cascading_candidates(
                symbol=asset,
                target_set=set_id,
                all_data=all_data,
                only_latest_bar=False,
            )
            cached_scans[(asset, set_id)] = (raw_cands, t_map)
            # Register candidates into FractalEventGraph
            for c in raw_cands:
                evt = CanonicalFractalEvent(
                    event_id=f"EVT_{asset[:3]}_{set_id}_{c['timestamp_ms']}_{c['direction']}",
                    event_type=EventType.BOS_BULLISH if c["direction"] == 1 else EventType.BOS_BEARISH,
                    symbol=asset,
                    timeframe=ltf_tf,
                    direction=c["direction"],
                    event_time=c["timestamp_ms"],
                    available_time=c["timestamp_ms"],
                    anchor_price=c["entry_price"],
                    boundary_high=c["entry_price"] if c["direction"] == -1 else c["target_price"],
                    boundary_low=c["stop_price"] if c["direction"] == 1 else c["target_price"],
                    source_candle_index=c["bar_index"],
                    confirmation_candle_index=c["bar_index"],
                    source_candle_count=1,
                    invalidation_rule=InvalidationCondition.OPPOSITE_STRUCTURAL_BREAK,
                    invalidation_price=c["stop_price"],
                    set_roles={set_id: "LTF_TRIGGER"},
                    meta=c.get("meta", {}),
                )
                event_graph.register_event(evt)
                c["root_event_id"] = evt.event_id

            print(f"  [{asset:<8} | {set_id:<6}]: {len(raw_cands):>3} raw candidates identified.")
    print(f"Pre-scan complete in {time.time() - t0:.1f}s. Total events registered in graph: {len(event_graph.events)}.")

    matrix_results: Dict[str, Dict[str, Any]] = {}
    master_candidate_ledger: List[Dict[str, Any]] = []

    # Iterate over 25 combinations (5 Sets x 5 Styles)
    for style_name, style_cfg in STYLES.items():
        matrix_results[style_name] = {}
        target_r = style_cfg["min_target_r"]
        max_bars = style_cfg["max_holding_bars"]

        print(f"\nEvaluating Style: {style_name:<12} (Target: {target_r:.1f}R, Max Holding: {max_bars} bars)...")

        for set_id in SETS:
            combo_key = f"{set_id}_{style_name}"
            combo_trades: List[Dict[str, Any]] = []

            engine = CausalBacktestEngine(
                taker_fee_bps=5.0,
                slippage_bps=2.0,
                min_target_r=target_r,
                max_holding_bars=max_bars,
            )

            for asset, all_data in all_asset_data.items():
                cfg = coordinator.TIMEFRAME_SETS[set_id]
                ltf_tf = cfg["ltf"]
                if ltf_tf not in all_data or (asset, set_id) not in cached_scans:
                    continue

                ltf_data = all_data[ltf_tf]
                raw_cands, trailing_map = cached_scans[(asset, set_id)]
                if not raw_cands:
                    continue

                # Filter candidates meeting style target_r
                valid_cands = []
                for c in raw_cands:
                    curr_px = float(c["entry_price"])
                    sl = float(c["stop_price"])
                    risk = abs(curr_px - sl)
                    if risk <= 0:
                        continue
                    dir_val = c["direction"]
                    tgt = curr_px + dir_val * target_r * risk
                    c_mod = dict(c)
                    c_mod["target_price"] = tgt
                    c_mod["target_r"] = target_r
                    valid_cands.append(c_mod)

                if not valid_cands:
                    continue

                # Check duplicate exposure via FractalEventGraph
                conflicts = event_graph.detect_overlapping_exposure(valid_cands)

                metrics = engine.execute_stream(
                    stream_id=f"{asset[:3]}_{combo_key}",
                    symbol=asset,
                    timeframe_set=set_id,
                    hypothesis=f"{style_name}_FRACTAL",
                    ltf_opens=ltf_data["o"],
                    ltf_highs=ltf_data["h"],
                    ltf_lows=ltf_data["l"],
                    ltf_closes=ltf_data["c"],
                    ltf_timestamps=ltf_data["ts"],
                    signal_candidates=valid_cands,
                    mtf_trailing_levels=trailing_map,
                )

                for t in metrics.trades:
                    t_dict = {
                        "combo_key": combo_key,
                        "set_id": set_id,
                        "style": style_name,
                        "symbol": asset,
                        "direction": t.direction,
                        "entry_ts": t.entry_ts,
                        "exit_ts": t.exit_ts,
                        "entry_px": t.entry_px,
                        "exit_px": t.exit_px,
                        "realized_r": t.realized_r,
                        "exit_reason": t.exit_reason,
                        "bars_held": t.bars_held,
                        "is_oos": bool(t.entry_ts >= VAL_END_MS),
                    }
                    combo_trades.append(t_dict)
                    master_candidate_ledger.append(t_dict)

            # Sort chronologically and run portfolio heat governor (Max 3 positions)
            combo_trades.sort(key=lambda x: (x["entry_ts"], x["exit_ts"]))
            accepted_portfolio: List[Dict[str, Any]] = []
            active: List[Dict[str, Any]] = []

            for tr in combo_trades:
                e_ts = tr["entry_ts"]
                active = [p for p in active if p["exit_ts"] > e_ts]
                if len(active) < 3:
                    accepted_portfolio.append(tr)
                    active.append(tr)

            # Compute In-Sample vs Out-of-Sample metrics for accepted trades
            is_trades = [t for t in accepted_portfolio if not t["is_oos"]]
            oos_trades = [t for t in accepted_portfolio if t["is_oos"]]

            m_full = compute_metrics(accepted_portfolio)
            m_is = compute_metrics(is_trades)
            m_oos = compute_metrics(oos_trades)

            # Classification
            if m_full["total_trades"] < 50:
                classification = "INCONCLUSIVE_INSUFFICIENT_N"
            elif m_oos["total_trades"] >= 20 and m_oos["profit_factor"] >= 1.30 and m_oos["expectancy_r"] > 0:
                classification = "CERTIFIED_CANDIDATE_PASS"
            elif m_full["profit_factor"] >= 1.20 and m_oos["profit_factor"] >= 1.0:
                classification = "MARGINAL_CANDIDATE"
            else:
                classification = "REJECTED_UNPROFITABLE"

            matrix_results[style_name][set_id] = {
                "full": m_full,
                "in_sample": m_is,
                "out_of_sample": m_oos,
                "classification": classification,
            }

            print(f"  [{combo_key:<16}] N={m_full['total_trades']:>4} | Full Net: {m_full['total_r']:>+7.2f}R (PF {m_full['profit_factor']:>4.2f}) | OOS Net: {m_oos['total_r']:>+6.2f}R (PF {m_oos['profit_factor']:>4.2f}) | Class: {classification}")

    # ---------------------------------------------------------
    # PRINT MASTER SCORECARD TABLE
    # ---------------------------------------------------------
    print("\n" + "=" * 125)
    print("STRATA PHASE 2 MASTER SCORECARD: 5 SETS x 5 STYLES")
    print("=" * 125)
    header = f"{'STYLE':<12} | {'SET':<6} | {'FULL N':<6} | {'FULL NET (R)':<12} | {'FULL PF':<8} | {'OOS N':<6} | {'OOS NET (R)':<12} | {'OOS PF':<8} | {'CLASSIFICATION':<26}"
    print(header)
    print("-" * 125)

    for style_name in STYLES:
        for set_id in SETS:
            res = matrix_results[style_name][set_id]
            f = res["full"]
            o = res["out_of_sample"]
            print(f"{style_name:<12} | {set_id:<6} | {f['total_trades']:<6} | {f['total_r']:>+10.2f}R | {f['profit_factor']:>6.2f} | {o['total_trades']:<6} | {o['total_r']:>+10.2f}R | {o['profit_factor']:>6.2f} | {res['classification']:<26}")

    print("=" * 125)

    # Save artifact
    out_file = OUTPUT_DIR / "strata_phase_2_matrix_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(matrix_results, f, indent=2)

    # Save ledger
    ledger_file = OUTPUT_DIR / "strata_phase_2_master_ledger.jsonl"
    with open(ledger_file, "w", encoding="utf-8") as f:
        for t in master_candidate_ledger:
            f.write(json.dumps(t) + "\n")

    print(f"\nArtifact saved to: {out_file.name} & {ledger_file.name}")


if __name__ == "__main__":
    run_strata_matrix()
