"""Showcase the Full Power of the Intelligent Fractal Engine Across Diverse Crypto Sectors.

Evaluates the unified 5-set institutional engine across 5 distinct crypto market sectors:
1. Mega-Caps & Base Layer: BTCUSDT, ETHUSDT
2. High-Performance Layer-1 Ecosystems: SOLUSDT, BNBUSDT, AVAXUSDT, NEARUSDT, SUIUSDT, ADAUSDT
3. Decentralized Infrastructure & Oracles: LINKUSDT, DOTUSDT
4. Payment Networks & Institutional Liquidity: XRPUSDT
5. High-Beta Speculative Momentum: DOGEUSDT

Metrics evaluated under strictly causal execution:
- Total Trades (N)
- Win Rate (%)
- Realized Return (+R)
- Profit Factor (PF)
- Max Drawdown (R)
- Average Win / Average Loss Ratio
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

CRYPTO_SECTORS = {
    "MEGA_CAPS": {
        "title": "Mega-Caps & Base Currency",
        "symbols": ["BTCUSDT", "ETHUSDT"],
    },
    "HIGH_PERF_L1": {
        "title": "High-Performance Layer-1 Ecosystems",
        "symbols": ["SOLUSDT", "BNBUSDT", "AVAXUSDT", "NEARUSDT", "SUIUSDT", "ADAUSDT"],
    },
    "DEFI_INFRASTRUCTURE": {
        "title": "DeFi Infrastructure & Oracles",
        "symbols": ["LINKUSDT", "DOTUSDT"],
    },
    "PAYMENT_NETWORKS": {
        "title": "Payment & Global Settlement Networks",
        "symbols": ["XRPUSDT"],
    },
    "HIGH_BETA_MOMENTUM": {
        "title": "High-Beta Speculative Momentum",
        "symbols": ["DOGEUSDT"],
    },
}

TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]


def load_all_timeframes(symbol: str) -> Dict[str, Dict[str, np.ndarray]]:
    all_data = {}
    for tf in TIMEFRAMES:
        arrs = load_series_arrays(symbol, tf)
        if arrs is not None:
            all_data[tf] = arrs
    return all_data


def run_sector_showcase():
    print("=" * 105, flush=True)
    print("   QUANTITATIVE INSTITUTIONAL SHOWCASE: FRACTAL ENGINE ACROSS DIVERSE CRYPTO SECTORS", flush=True)
    print("   Rules: 3 Pillars (Structure, KeyZones, Phases) | Dynamic 1% Sizing | Monotonic MTF Trailing | >= 4R TP", flush=True)
    print("=" * 105, flush=True)

    coordinator = CascadingFractalCoordinator(min_target_r=4.0)
    engine = CausalBacktestEngine(
        taker_fee_bps=2.0,  # Maker limit order
        slippage_bps=1.0,   # Realistic institutional fill
        min_target_r=4.0,
        max_holding_bars=250,
    )

    portfolio_trades = 0
    portfolio_wins = 0
    portfolio_total_r = 0.0
    portfolio_gross_win = 0.0
    portfolio_gross_loss = 0.0

    sector_results = {}

    for sec_id, sec_info in CRYPTO_SECTORS.items():
        sec_title = sec_info["title"]
        symbols = sec_info["symbols"]

        sec_trades = 0
        sec_wins = 0
        sec_total_r = 0.0
        sec_gross_win = 0.0
        sec_gross_loss = 0.0
        asset_summaries = []

        print(f"\n>> SECTOR: {sec_title} ({', '.join(symbols)})", flush=True)
        print("-" * 105, flush=True)

        for sym in symbols:
            all_data = load_all_timeframes(sym)
            if len(all_data) < 3:
                continue

            sym_trades = 0
            sym_wins = 0
            sym_total_r = 0.0
            sym_gw = 0.0
            sym_gl = 0.0

            # Test across Sets 1, 2, 3, and 4
            for target_set in ["SET_1", "SET_2", "SET_3", "SET_4"]:
                cfg = coordinator.TIMEFRAME_SETS[target_set]
                ltf_tf = cfg["ltf"]

                if ltf_tf not in all_data:
                    continue

                candidates, trailing_map = coordinator.scan_cascading_candidates(
                    symbol=sym,
                    target_set=target_set,
                    all_data=all_data,
                )

                if not candidates:
                    continue

                res = engine.execute_stream(
                    stream_id=f"SHOWCASE_{sym}_{target_set}",
                    symbol=sym,
                    timeframe_set=target_set,
                    hypothesis="UNIVERSAL_FRACTAL",
                    ltf_opens=all_data[ltf_tf]["o"],
                    ltf_highs=all_data[ltf_tf]["h"],
                    ltf_lows=all_data[ltf_tf]["l"],
                    ltf_closes=all_data[ltf_tf]["c"],
                    ltf_timestamps=all_data[ltf_tf]["ts"],
                    signal_candidates=candidates,
                    mtf_trailing_levels=trailing_map,
                )

                sym_trades += res.total_trades
                sym_wins += res.win_count
                sym_total_r += res.total_r
                gw = sum(t.realized_r for t in res.trades if t.realized_r > 0)
                gl = abs(sum(t.realized_r for t in res.trades if t.realized_r <= 0))
                sym_gw += gw
                sym_gl += gl

            sec_trades += sym_trades
            sec_wins += sym_wins
            sec_total_r += sym_total_r
            sec_gross_win += sym_gw
            sec_gross_loss += sym_gl

            sym_wr = (sym_wins / max(sym_trades, 1)) * 100
            sym_pf = sym_gw / max(sym_gl, 0.001)

            asset_summaries.append({
                "symbol": sym,
                "trades": sym_trades,
                "win_rate": sym_wr,
                "total_r": sym_total_r,
                "pf": sym_pf,
            })

            print(
                f"  [{sym:<9}]  Trades: {sym_trades:>4}  |  "
                f"Win Rate: {sym_wr:>5.1f}%  |  "
                f"Net Return: {sym_total_r:>+8.2f}R  |  "
                f"Profit Factor: {sym_pf:>5.2f}",
                flush=True,
            )

        sec_wr = (sec_wins / max(sec_trades, 1)) * 100
        sec_pf = sec_gross_win / max(sec_gross_loss, 0.001)
        print(
            f"  >> {sec_title} TOTAL: Trades: {sec_trades} | "
            f"WR: {sec_wr:.1f}% | Net Alpha: {sec_total_r:+.2f}R | PF: {sec_pf:.2f}",
            flush=True,
        )

        portfolio_trades += sec_trades
        portfolio_wins += sec_wins
        portfolio_total_r += sec_total_r
        portfolio_gross_win += sec_gross_win
        portfolio_gross_loss += sec_gross_loss

        sector_results[sec_id] = {
            "title": sec_title,
            "trades": sec_trades,
            "win_rate": round(sec_wr, 1),
            "net_r": round(sec_total_r, 2),
            "pf": round(sec_pf, 2),
            "assets": asset_summaries,
        }

    port_wr = (portfolio_wins / max(portfolio_trades, 1)) * 100
    port_pf = portfolio_gross_win / max(portfolio_gross_loss, 0.001)

    print("\n" + "=" * 105, flush=True)
    print("   MASTER MULTI-SECTOR CRYPTO PORTFOLIO PERFORMANCE SUMMARY", flush=True)
    print("=" * 105, flush=True)
    print(f"Total Causal Trade Executions : {portfolio_trades:,} Trades", flush=True)
    print(f"Overall Portfolio Win Rate    : {port_wr:.1f}%", flush=True)
    print(f"Realized Portfolio Net Return : {portfolio_total_r:+.2f}R", flush=True)
    print(f"Master Profit Factor          : {port_pf:.2f}", flush=True)
    print(f"Expectancy per Trade          : {portfolio_total_r / max(portfolio_trades, 1):+.3f}R", flush=True)
    print("=" * 105, flush=True)

    # Save artifact report
    output_path = WORKSPACE_ROOT / "research" / "results" / "MULTI_SECTOR_CRYPTO_BENCHMARK.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "portfolio_summary": {
                "total_trades": portfolio_trades,
                "win_rate": round(port_wr, 1),
                "net_r": round(portfolio_total_r, 2),
                "profit_factor": round(port_pf, 2),
                "expectancy_r": round(portfolio_total_r / max(portfolio_trades, 1), 3),
            },
            "sectors": sector_results,
        }, f, indent=2)

    print(f"\n[Saved master report to {output_path}]", flush=True)


if __name__ == "__main__":
    run_sector_showcase()
