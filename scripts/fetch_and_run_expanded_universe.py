"""Expanded Universe Fetcher & Cascading Fractal Validator.

Fetches real multi-timeframe OHLCV data from Binance Public REST API for top crypto assets,
validates all candlestick invariants, and executes the Cascading Fractal Coordinator
across the expanded 12-asset crypto universe.

Assets:
- BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT (Original core)
- XRPUSDT, DOGEUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, NEARUSDT, SUIUSDT, DOTUSDT (New expansion)
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

NEW_ASSETS = [
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
    "LINKUSDT", "NEARUSDT", "SUIUSDT", "DOTUSDT"
]

ALL_ASSETS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT",
    "LINKUSDT", "NEARUSDT", "SUIUSDT", "DOTUSDT"
]

TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]


def fetch_binance_klines(symbol: str, interval: str, limit: int = 1000) -> Optional[List[List]]:
    """Fetch raw klines directly from Binance Public REST API."""
    url = f"{BINANCE_KLINES_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                # Filter to [open_time, open, high, low, close, volume]
                rows = []
                for b in data:
                    rows.append([
                        int(b[0]), float(b[1]), float(b[2]),
                        float(b[3]), float(b[4]), float(b[5])
                    ])
                rows.sort(key=lambda x: x[0])
                return rows
    except Exception as e:
        print(f"  [ERROR] Failed to fetch {symbol} {interval}: {e}")
        return None


def ensure_expanded_data():
    """Ensure all 12 assets have cached series across all 7 timeframes."""
    print("\n[1/3] Ensuring Data Availability for Top 12 Crypto Assets...")
    for symbol in NEW_ASSETS:
        for tf in TIMEFRAMES:
            cache_file = CACHE_DIR / f"binance_{symbol}_{tf}.json"
            if not cache_file.exists() or cache_file.stat().st_size < 100:
                print(f"  Fetching {symbol} {tf} from Binance API...", flush=True)
                rows = fetch_binance_klines(symbol, tf, limit=1000)
                if rows:
                    # Invariant validation
                    valid = True
                    for r in rows:
                        t, o, h, l, c, v = r
                        if not (l <= o <= h and l <= c <= h and l <= h and v >= 0):
                            valid = False
                            break
                    if valid:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(rows, f)
                time.sleep(0.08)  # Polite API pacing


def load_all_7_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in TIMEFRAMES:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_expanded_backtest():
    """Runs Cascading Fractal Coordinator across all 12 assets on Sets 1, 2, and 3."""
    print("\n[2/3] Running Cascading Fractal Backtest across Top 12 Crypto Assets...")
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

    # Core Institutional Sets: 1, 2, 3
    target_sets = ["SET_1", "SET_2", "SET_3"]
    results_by_set: Dict[str, Dict[str, Any]] = {
        s: {"trades": 0, "wins": 0, "total_r": 0.0, "gross_win_r": 0.0, "gross_loss_r": 0.0}
        for s in target_sets
    }
    asset_summaries: Dict[str, Dict[str, float]] = {}
    all_trades: List[Dict[str, Any]] = []

    for asset in ALL_ASSETS:
        all_data = load_all_7_timeframes(asset)
        if len(all_data) < 4:
            print(f"  [{asset}] Insufficient timeframe coverage ({len(all_data)}/7). Skipping.")
            continue

        asset_tot_r = 0.0
        asset_trades_count = 0

        for target_set in target_sets:
            stream_id = f"CASCADE_{asset}_{target_set}"
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
            elapsed = time.time() - t0

            if not candidates:
                continue

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

            # Update set statistics
            s_dict = results_by_set[target_set]
            s_dict["trades"] += metrics.total_trades
            s_dict["wins"] += metrics.win_count
            s_dict["total_r"] += metrics.total_r
            s_dict["gross_win_r"] += sum(t.realized_r for t in metrics.trades if t.realized_r > 0)
            s_dict["gross_loss_r"] += abs(sum(t.realized_r for t in metrics.trades if t.realized_r <= 0))

            asset_tot_r += metrics.total_r
            asset_trades_count += metrics.total_trades

            for t in metrics.trades:
                all_trades.append({
                    "symbol": asset,
                    "set": target_set,
                    "direction": t.direction,
                    "realized_r": t.realized_r,
                    "exit_reason": t.exit_reason,
                    "bars_held": t.bars_held,
                })

            print(
                f"  [{asset:<8} {target_set}] N={metrics.total_trades:>3} | "
                f"WR={metrics.win_rate*100:>5.1f}% | "
                f"ExpR={metrics.expectancy_r:>6.3f} | "
                f"TotR={metrics.total_r:>7.2f} | "
                f"PF={metrics.profit_factor:>5.2f} | {elapsed:.2f}s",
                flush=True,
            )

        asset_summaries[asset] = {
            "total_trades": asset_trades_count,
            "net_r": round(asset_tot_r, 2),
        }

    # Summary Output
    print("\n" + "=" * 100)
    print("EXPANDED 12-CRYPTO UNIVERSE CASCADING RESULTS (SETS 1, 2, 3)")
    print("=" * 100)
    for s_name, s_data in results_by_set.items():
        n = s_data["trades"]
        wr = s_data["wins"] / max(n, 1) * 100
        pf = s_data["gross_win_r"] / max(s_data["gross_loss_r"], 0.001)
        tot_r = s_data["total_r"]
        exp_r = tot_r / max(n, 1)
        print(f"  {s_name:<8}: N={n:>5} Trades | Win Rate={wr:>5.1f}% | Expectancy={exp_r:>+6.3f}R | Profit Factor={pf:>5.2f} | Net R={tot_r:>+8.2f}R")

    total_all_trades = len(all_trades)
    net_all_r = sum(t["realized_r"] for t in all_trades)
    all_wins = [t for t in all_trades if t["realized_r"] > 0]
    all_losses = [t for t in all_trades if t["realized_r"] <= 0]
    total_wr = len(all_wins) / max(total_all_trades, 1) * 100
    overall_pf = sum(t["realized_r"] for t in all_wins) / max(abs(sum(t["realized_r"] for t in all_losses)), 0.001)

    print("-" * 100)
    print(f"  PORTFOLIO TOTAL: {total_all_trades} Causal Trades | Win Rate={total_wr:.1f}% | Net Return={net_all_r:+.2f}R | Profit Factor={overall_pf:.2f}")
    print("=" * 100)

    # Save to disk
    out_dir = WORKSPACE_ROOT / "research" / "results" / "EXPANDED_UNIVERSE_RESULTS"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "master_expanded_universe_validation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "total_trades": total_all_trades,
            "win_rate_pct": round(total_wr, 2),
            "net_r": round(net_all_r, 2),
            "profit_factor": round(overall_pf, 3),
            "by_set": results_by_set,
            "by_asset": asset_summaries,
        }, f, indent=2)
    print(f"\n[3/3] Results saved to: {out_path}")


if __name__ == "__main__":
    ensure_expanded_data()
    run_expanded_backtest()
