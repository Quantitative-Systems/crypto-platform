"""
Quantitative Systems Platform (QSP) — Comprehensive Multi-Set Backtest Engine.

Executes systematic, causal backtesting using the certified StrategyExecutor across
ALL 6 TIMEFRAME SETS:
- Set 1: 1M / 1w / 1d (Macro / Position)
- Set 2: 1w / 1d / 4h (Swing)
- Set 3: 1d / 4h / 1h (Swing / Intraday)
- Set 4: 4h / 1h / 15m (Intraday)
- Set 5: 1h / 15m / 5m (Short-Term Intraday)
- Set 6: 15m / 5m / 1m (Scalping)

Assets: BTC/USDT, ETH/USDT, SOL/USDT.
Evaluates across chronological horizons (Lifetime, Dev 2021-2022, Val 2023, OOS 2024-2026).
Outputs complete empirical matrix to research/results/MULTISET_COMPREHENSIVE_BACKTEST_MATRIX.json.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.strategy_generator import StrategyExecutor
from research.discovery_lab.oos_manager import OOSManager

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUTPUT_MATRIX_FILE = os.path.join(RESULTS_DIR, "MULTISET_COMPREHENSIVE_BACKTEST_MATRIX.json")


def run_comprehensive_multiset_audit():
    print("=" * 95)
    print("QUANTITATIVE SYSTEMS PLATFORM — COMPREHENSIVE MULTI-SET BACKTEST BATTERY")
    print("Evaluating Sets 1 to 6 across BTC/USDT, ETH/USDT, SOL/USDT using StrategyExecutor")
    print("Epochs: Lifetime, Development (2021-2022), Validation (2023), OOS (2024-2026)")
    print("=" * 95)

    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    results_matrix = {}

    for set_name, sinfo in TIMEFRAME_SETS.items():
        print(f"\n================================================================================")
        print(f"[{set_name.upper()}] Triad: {sinfo['HTF']} -> {sinfo['MTF']} -> {sinfo['LTF']} | Style: {sinfo['style']}")
        print(f"================================================================================")

        results_matrix[set_name] = {"info": sinfo, "assets": {}}

        for sym in symbols:
            c_h = load_candles(sym, sinfo["HTF"]) or []
            c_m = load_candles(sym, sinfo["MTF"]) or []
            c_l = load_candles(sym, sinfo["LTF"]) or []

            clean_sym = sym.replace("/", "")
            strat_id = f"FAM-07-MTFCONT_{clean_sym}_{set_name.replace(' ', '')}"

            if len(c_h) < 25 or len(c_m) < 25 or len(c_l) < 50:
                print(f"  {sym:8s} | INSUFFICIENT_DATA (HTF: {len(c_h)}, MTF: {len(c_m)}, LTF: {len(c_l)})")
                results_matrix[set_name]["assets"][sym] = {
                    "status": "INSUFFICIENT_DATA",
                    "reason": f"Bar count too low for 3-tier warmup (HTF: {len(c_h)}, MTF: {len(c_m)}, LTF: {len(c_l)})",
                }
                continue

            executor = StrategyExecutor(sym, set_name, c_h, c_m, c_l)

            # 1. Lifetime (all available data)
            life_res = executor.run_family_7_mtf_continuation(
                start_ts=0,
                end_ts=9999999999,
            )
            m_life = life_res.get("metrics", {})

            # 2. Development (2021-2022)
            dev_res = executor.run_family_7_mtf_continuation(
                start_ts=OOSManager.DEV_START_TS,
                end_ts=OOSManager.DEV_END_TS,
            )
            m_dev = dev_res.get("metrics", {})

            # 3. Validation (2023)
            val_res = executor.run_family_7_mtf_continuation(
                start_ts=OOSManager.VAL_START_TS,
                end_ts=OOSManager.VAL_END_TS,
            )
            m_val = val_res.get("metrics", {})

            # 4. Out-of-Sample (2024-2026)
            oos_res = executor.run_family_7_mtf_continuation(
                start_ts=OOSManager.OOS_START_TS,
                end_ts=9999999999,
            )
            m_oos = oos_res.get("metrics", {})

            total_trades = m_life.get("total_trades", 0)
            net_r = m_life.get("net_r", 0.0)
            wr = m_life.get("win_rate", 0.0) * 100.0
            pf = m_life.get("profit_factor", 0.0)
            max_dd = m_life.get("max_drawdown_r", 0.0)

            results_matrix[set_name]["assets"][sym] = {
                "strategy_id": strat_id,
                "status": "EVALUATED",
                "lifetime": m_life,
                "development": m_dev,
                "validation": m_val,
                "oos": m_oos,
            }

            print(
                f"  {sym:8s} | Lifetime N={total_trades:5d} | Net R={'+' if net_r >= 0 else ''}{net_r:8.2f}R | "
                f"WR={wr:4.1f}% | PF={pf:4.2f} | Max DD={max_dd:5.2f}R | "
                f"Dev: {'+' if m_dev.get('net_r', 0) >= 0 else ''}{m_dev.get('net_r', 0):.1f}R (N={m_dev.get('total_trades', 0)}), "
                f"Val: {'+' if m_val.get('net_r', 0) >= 0 else ''}{m_val.get('net_r', 0):.1f}R (N={m_val.get('total_trades', 0)}), "
                f"OOS: {'+' if m_oos.get('net_r', 0) >= 0 else ''}{m_oos.get('net_r', 0):.1f}R (N={m_oos.get('total_trades', 0)})"
            )

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(OUTPUT_MATRIX_FILE, "w") as f:
        json.dump(results_matrix, f, indent=2)

    print(f"\n================================================================================")
    print(f"[COMPLETE] Multi-Set comprehensive backtest matrix written to:")
    print(f"           -> {OUTPUT_MATRIX_FILE}")
    print(f"================================================================================")


if __name__ == "__main__":
    run_comprehensive_multiset_audit()
