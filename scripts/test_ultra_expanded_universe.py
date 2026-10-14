"""Ultra-Expanded Crypto Universe Validation Script.

Fetches data and stress-tests the Cascading Fractal Coordinator across 8 additional
diverse crypto assets spanning multiple sectors:
- Next-Gen L1: APTUSDT, INJUSDT, ATOMUSDT
- Ethereum Layer-2 Rollups: OPUSDT, ARBUSDT
- Legacy PoW & Payments: LTCUSDT
- Modular Infrastructure: TIAUSDT
- AI & DePIN Compute: RENDERUSDT

Audits performance under identical causal conditions:
- Zero lookahead
- 1% dynamic risk sizing
- Monotonic MTF trailing
- >= 4.0R destination targets
- 5 bps taker fee, 2 bps slippage
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.backtest.engine import CausalBacktestEngine
from market_model.cascading_fractal_coordinator import CascadingFractalCoordinator
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

CACHE_DIR = WORKSPACE_ROOT / "market_data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

NEW_EXPANSION_ASSETS = [
    "APTUSDT",      # Next-Gen Move L1
    "OPUSDT",       # Optimism L2 Rollup
    "ARBUSDT",      # Arbitrum L2 Rollup
    "INJUSDT",      # Injective DeFi L1
    "TIAUSDT",      # Celestia Modular DA
    "RENDERUSDT",   # Render DePIN / AI
    "ATOMUSDT",     # Cosmos Interchain Hub
    "LTCUSDT",      # Legacy PoW Payment
]

TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]


def fetch_binance_klines(symbol: str, interval: str, limit: int = 1000) -> Optional[List[List]]:
    """Fetch raw klines from Binance Public REST API."""
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                rows = []
                for b in data:
                    rows.append([
                        int(b[0]), float(b[1]), float(b[2]),
                        float(b[3]), float(b[4]), float(b[5])
                    ])
                rows.sort(key=lambda x: x[0])
                return rows
    except Exception as e:
        print(f"    [WARN] Failed {symbol} {interval}: {e}", flush=True)
        return None


def ensure_asset_data(symbol: str):
    """Download data for an asset across all 7 timeframes if not already cached."""
    print(f"  [DATA] Checking/fetching data for {symbol}...", flush=True)
    for tf in TIMEFRAMES:
        cache_file = CACHE_DIR / f"binance_{symbol}_{tf}.json"
        if not cache_file.exists() or cache_file.stat().st_size < 100:
            rows = fetch_binance_klines(symbol, tf, limit=1000)
            if rows:
                valid = True
                for r in rows:
                    t, o, h, l, c, v = r
                    if not (l <= o <= h and l <= c <= h and l <= h and v >= 0):
                        valid = False
                        break
                if valid:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(rows, f)
            time.sleep(0.08)


def load_asset_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in TIMEFRAMES:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_ultra_expansion_validation():
    print("=" * 105, flush=True)
    print("   ULTRA-EXPANDED CRYPTO UNIVERSE VALIDATION: PROVING STATISTICAL EDGE ON UNSEEN ASSETS", flush=True)
    print("   Assets: L1s (APT, INJ, ATOM), L2s (OP, ARB), AI/DePIN (RENDER), Modular (TIA), PoW (LTC)", flush=True)
    print("   Rules: Canonical 3 Pillars | Dynamic 1% Sizing | Monotonic MTF Trailing | >= 4R TP", flush=True)
    print("=" * 105, flush=True)

    # Step 1: Ensure Data
    for sym in NEW_EXPANSION_ASSETS:
        ensure_asset_data(sym)

    # Step 2: Initialize Institutional Coordinator & Engine
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

    target_sets = ["SET_1", "SET_2", "SET_3"]
    results_by_set: Dict[str, Dict[str, Any]] = {
        s: {"trades": 0, "wins": 0, "total_r": 0.0, "gross_win_r": 0.0, "gross_loss_r": 0.0}
        for s in target_sets
    }
    asset_metrics: Dict[str, Dict[str, Any]] = {}
    total_trades_all = 0
    total_wins_all = 0
    total_r_all = 0.0
    gross_win_all = 0.0
    gross_loss_all = 0.0

    print("\n" + "-" * 105, flush=True)
    print(f"{'ASSET':<10} | {'SET_1 (Macro)':<18} | {'SET_2 (Swing)':<18} | {'SET_3 (Intraday)':<18} | {'TOTAL ALPHA':<16} | {'PF':<6}", flush=True)
    print("-" * 105, flush=True)

    for asset in NEW_EXPANSION_ASSETS:
        all_data = load_asset_timeframes(asset)
        if len(all_data) < 4:
            print(f"  [{asset:<8}] Insufficient timeframes ({len(all_data)}/7). Skipping.")
            continue

        sym_total_r = 0.0
        sym_trades = 0
        sym_wins = 0
        sym_gw = 0.0
        sym_gl = 0.0
        row_cells = []

        for target_set in target_sets:
            cfg = coordinator.TIMEFRAME_SETS[target_set]
            ltf_tf = cfg["ltf"]

            if ltf_tf not in all_data:
                row_cells.append("N/A")
                continue

            candidates, trailing_map = coordinator.scan_cascading_candidates(
                symbol=asset,
                target_set=target_set,
                all_data=all_data,
            )

            if not candidates:
                row_cells.append("0.0R (N=0)")
                continue

            metrics = engine.execute_stream(
                stream_id=f"ULTRA_{asset}_{target_set}",
                symbol=asset,
                timeframe_set=target_set,
                hypothesis="CASCADING_BATON",
                ltf_opens=all_data[ltf_tf]["o"],
                ltf_highs=all_data[ltf_tf]["h"],
                ltf_lows=all_data[ltf_tf]["l"],
                ltf_closes=all_data[ltf_tf]["c"],
                ltf_timestamps=all_data[ltf_tf]["ts"],
                signal_candidates=candidates,
                mtf_trailing_levels=trailing_map,
            )

            gw = sum(t.realized_r for t in metrics.trades if t.realized_r > 0)
            gl = abs(sum(t.realized_r for t in metrics.trades if t.realized_r <= 0))

            s_dict = results_by_set[target_set]
            s_dict["trades"] += metrics.total_trades
            s_dict["wins"] += metrics.win_count
            s_dict["total_r"] += metrics.total_r
            s_dict["gross_win_r"] += gw
            s_dict["gross_loss_r"] += gl

            sym_trades += metrics.total_trades
            sym_wins += metrics.win_count
            sym_total_r += metrics.total_r
            sym_gw += gw
            sym_gl += gl

            wr = metrics.win_rate * 100
            cell = f"{metrics.total_r:+.1f}R (N={metrics.total_trades}, {wr:.0f}%)"
            row_cells.append(cell)

        sym_pf = sym_gw / max(sym_gl, 0.001) if sym_gl > 0 else (99.0 if sym_gw > 0 else 0.0)
        tot_cell = f"{sym_total_r:+.2f}R (N={sym_trades})"
        print(f"{asset:<10} | {row_cells[0]:<18} | {row_cells[1]:<18} | {row_cells[2]:<18} | {tot_cell:<16} | {sym_pf:>5.2f}", flush=True)

        asset_metrics[asset] = {
            "trades": sym_trades,
            "wins": sym_wins,
            "win_rate_pct": round((sym_wins / max(sym_trades, 1)) * 100, 1),
            "net_r": round(sym_total_r, 2),
            "profit_factor": round(sym_pf, 2),
        }

        total_trades_all += sym_trades
        total_wins_all += sym_wins
        total_r_all += sym_total_r
        gross_win_all += sym_gw
        gross_loss_all += sym_gl

    port_wr = (total_wins_all / max(total_trades_all, 1)) * 100
    port_pf = gross_win_all / max(gross_loss_all, 0.001)

    print("=" * 105, flush=True)
    print("   ULTRA-EXPANDED SUMMARY BY TIMEFRAME SET", flush=True)
    print("=" * 105, flush=True)
    for s_name, s_data in results_by_set.items():
        n = s_data["trades"]
        wr = (s_data["wins"] / max(n, 1)) * 100
        pf = s_data["gross_win_r"] / max(s_data["gross_loss_r"], 0.001)
        tot_r = s_data["total_r"]
        exp_r = tot_r / max(n, 1)
        print(f"  {s_name:<8}: N={n:>4} Trades | Win Rate={wr:>5.1f}% | Expectancy={exp_r:>+6.3f}R | Profit Factor={pf:>5.2f} | Net Alpha={tot_r:>+8.2f}R", flush=True)

    print("-" * 105, flush=True)
    print(f"  TOTAL NEW EXPANSION PORTFOLIO: {total_trades_all} Trades | Win Rate: {port_wr:.1f}% | Net Alpha: {total_r_all:+.2f}R | Profit Factor: {port_pf:.2f}", flush=True)
    print("=" * 105, flush=True)

    # Save to json artifact
    out_dir = WORKSPACE_ROOT / "research" / "results" / "EXPANDED_UNIVERSE_RESULTS"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ultra_expanded_universe_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_trades": total_trades_all,
            "win_rate_pct": round(port_wr, 1),
            "net_r": round(total_r_all, 2),
            "profit_factor": round(port_pf, 2),
            "by_set": results_by_set,
            "by_asset": asset_metrics,
        }, f, indent=2)

    print(f"\nSaved detailed verification artifact to: {out_file}", flush=True)


if __name__ == "__main__":
    run_ultra_expansion_validation()
