"""
Quantitative Systems Platform (QSP) — Systematic Strategies Research Division.
Phase E: Cross-Asset Correlation & Portfolio Risk Aggregation.

Evaluates:
1. Pairwise trade return correlation across all 5 qualified candidate strategies.
2. Signal concurrency & portfolio heat (% time with 0, 1, 2, 3, 4, 5 concurrent positions).
3. Portfolio-level aggregate equity curves and drawdown under:
   - Scheme A: Unconstrained Heat (Independent 1.0% risk per strategy)
   - Scheme B: Institutional Portfolio Heat Cap (Max 3.0% total concurrent portfolio risk)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.strategy_generator import StrategyExecutor

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
VAL_OOS_FILE = os.path.join(RESULTS_DIR, "validation_and_oos_results.json")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "AUDIT_PHASE_E_PORTFOLIO_RISK.json")


def run_phase_e_audit():
    print("=" * 90)
    print("PHASE E: CROSS-ASSET CORRELATION & PORTFOLIO RISK AGGREGATION")
    print("=" * 90)

    if not os.path.exists(VAL_OOS_FILE):
        raise FileNotFoundError(f"Missing {VAL_OOS_FILE}")

    with open(VAL_OOS_FILE, "r") as f:
        val_oos_records = json.load(f)

    qualified = [r for r in val_oos_records if r["final_status"] == "QUALIFIED_ROBUST"]
    print(f"Evaluating portfolio interactions for {len(qualified)} QUALIFIED_ROBUST candidates...")

    strategy_trades = {}
    candidate_ids = []

    # Run each strategy over full 2021-2026 horizon to extract trades
    for cand in qualified:
        cid = cand["candidate_id"]
        symbol = cand["symbol"]
        set_id = cand["set"]
        fam_id = cand["family_id"]
        candidate_ids.append(cid)

        sc = TIMEFRAME_SETS[set_id]
        htf = load_candles(symbol, sc["HTF"])
        mtf = load_candles(symbol, sc["MTF"])
        ltf = load_candles(symbol, sc["LTF"])

        method_name = "run_family_7_mtf_continuation" if fam_id == "FAM-07-MTFCONT" else "run_family_4_momentum"
        exec_cand = StrategyExecutor(
            symbol, set_id, htf, mtf, ltf,
            start_ts=OOSManager.DEV_START_TS, end_ts=1788307200
        )
        res = getattr(exec_cand, method_name)()
        strategy_trades[cid] = res["trades"]

    # 1. Align returns onto a daily time grid (2021-01-01 to 2026-06-30)
    daily_start_ts = OOSManager.DEV_START_TS
    daily_end_ts = 1788307200
    day_seconds = 86400

    days_index = list(range(daily_start_ts, daily_end_ts, day_seconds))
    daily_pnl = {cid: np.zeros(len(days_index)) for cid in candidate_ids}

    # Populate daily PnL (realized Net R attributed to exit day)
    for cid, trades in strategy_trades.items():
        for t in trades:
            exit_ts = t["exit_ts"]
            idx = int((exit_ts - daily_start_ts) // day_seconds)
            if 0 <= idx < len(days_index):
                daily_pnl[cid][idx] += t["realized_r"]

    pnl_df = pd.DataFrame(daily_pnl)

    # 2. Pairwise Pearson correlation matrix
    corr_matrix = pnl_df.corr().round(4).to_dict()

    # 3. Concurrent position analysis on a 4-hour time grid
    four_hour_sec = 14400
    four_h_index = list(range(daily_start_ts, daily_end_ts, four_hour_sec))
    concurrency_grid = np.zeros(len(four_h_index), dtype=int)

    for cid, trades in strategy_trades.items():
        for t in trades:
            e_ts = t["entry_ts"]
            x_ts = t["exit_ts"]
            start_idx = max(0, int((e_ts - daily_start_ts) // four_hour_sec))
            end_idx = min(len(four_h_index) - 1, int((x_ts - daily_start_ts) // four_hour_sec))
            concurrency_grid[start_idx:end_idx + 1] += 1

    concurrency_counts = {int(k): int(np.sum(concurrency_grid == k)) for k in range(len(candidate_ids) + 1)}
    total_grid_points = len(four_h_index)
    concurrency_pct = {k: round(v / total_grid_points * 100, 2) for k, v in concurrency_counts.items()}

    # 4. Portfolio Simulation: Unconstrained vs Heat-Capped
    # Unconstrained: sum of daily R across all strategies
    unconstrained_daily_r = pnl_df.sum(axis=1).values
    unconstrained_cum_r = np.cumsum(unconstrained_daily_r)
    unconstrained_peak = np.maximum.accumulate(unconstrained_cum_r)
    unconstrained_drawdowns = unconstrained_peak - unconstrained_cum_r
    unconstrained_max_dd = float(np.max(unconstrained_drawdowns))
    unconstrained_total_net_r = float(unconstrained_cum_r[-1])

    # Scheme B: Fixed-Fractional Slot Allocation (0.60% risk per trade)
    # With 5 strategies, max concurrent exposure is strictly 5 * 0.60% = 3.00% equity at all times.
    fixed_slot_risk_pct = 0.006  # 0.60%
    slot_scale = fixed_slot_risk_pct / 0.01  # 0.60
    slot_daily_r = unconstrained_daily_r * slot_scale
    slot_cum_r = np.cumsum(slot_daily_r)
    slot_peak = np.maximum.accumulate(slot_cum_r)
    slot_drawdowns = slot_peak - slot_cum_r
    slot_max_dd = float(np.max(slot_drawdowns))
    slot_total_net_r = float(slot_cum_r[-1])

    # Scheme C: Dynamic Heat Cap (Daily scaling when concurrency > 3)
    capped_daily_r = np.zeros(len(days_index))
    for i in range(len(days_index)):
        day_ts = days_index[i]
        idx_4h_start = int((day_ts - daily_start_ts) // four_hour_sec)
        idx_4h_end = min(len(concurrency_grid), idx_4h_start + 6)
        day_max_concur = int(np.max(concurrency_grid[idx_4h_start:idx_4h_end])) if idx_4h_start < len(concurrency_grid) else 1

        scale = 1.0
        if day_max_concur > 3:
            scale = 3.0 / float(day_max_concur)

        capped_daily_r[i] = np.sum([pnl_df[cid].iloc[i] * scale for cid in candidate_ids])

    capped_cum_r = np.cumsum(capped_daily_r)
    capped_peak = np.maximum.accumulate(capped_cum_r)
    capped_drawdowns = capped_peak - capped_cum_r
    capped_max_dd = float(np.max(capped_drawdowns))
    capped_total_net_r = float(capped_cum_r[-1])

    print("\n--- Portfolio Correlation Matrix (Daily Net R) ---")
    for cid in candidate_ids:
        print(f"  {cid[:25]:25s}: " + " | ".join([f"{corr_matrix[cid][c2]:+5.2f}" for c2 in candidate_ids]))

    print("\n--- Concurrency Distribution (4-Hour Grid) ---")
    for k in sorted(concurrency_pct.keys()):
        print(f"  Concurrent Positions {k}: {concurrency_pct[k]:5.1f}% of time")

    print("\n--- Portfolio Aggregation Performance ---")
    print(f"  Unconstrained (1% per trade): Total Net R = {unconstrained_total_net_r:+7.2f}R | Max DD = {unconstrained_max_dd:5.2f}R | Calmar = {unconstrained_total_net_r/unconstrained_max_dd:.2f}")
    print(f"  Fixed Slot (0.6% risk, Max 3% Heat): Total Net R = {slot_total_net_r:+7.2f}R | Max DD = {slot_max_dd:5.2f}R | Calmar = {slot_total_net_r/slot_max_dd:.2f}")
    print(f"  Dynamic Capped (Max 3% total): Total Net R = {capped_total_net_r:+7.2f}R | Max DD = {capped_max_dd:5.2f}R | Calmar = {capped_total_net_r/capped_max_dd:.2f}")

    manifest = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_phase": "PHASE_E_PORTFOLIO_CORRELATION_AND_RISK",
        "governance": "Quantitative Systems Platform (QSP) Research Division",
        "candidate_ids": candidate_ids,
        "pairwise_correlation_matrix": corr_matrix,
        "concurrency_distribution_pct": concurrency_pct,
        "portfolio_performance": {
            "unconstrained_1pct_heat": {
                "total_net_r": round(unconstrained_total_net_r, 2),
                "max_drawdown_r": round(unconstrained_max_dd, 2),
                "calmar_ratio": round(unconstrained_total_net_r / unconstrained_max_dd, 3) if unconstrained_max_dd > 0 else 0.0,
            },
            "fixed_slot_0.6pct_heat": {
                "total_net_r": round(slot_total_net_r, 2),
                "max_drawdown_r": round(slot_max_dd, 2),
                "calmar_ratio": round(slot_total_net_r / slot_max_dd, 3) if slot_max_dd > 0 else 0.0,
                "max_concurrent_portfolio_heat_pct": 3.0,
            },
            "dynamic_capped_3pct_heat": {
                "total_net_r": round(capped_total_net_r, 2),
                "max_drawdown_r": round(capped_max_dd, 2),
                "calmar_ratio": round(capped_total_net_r / capped_max_dd, 3) if capped_max_dd > 0 else 0.0,
            }
        }
    }


    with open(OUTPUT_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 90)
    print("AUDIT PHASE E COMPLETE.")
    print(f"Report saved to: {OUTPUT_FILE}")
    print("=" * 90)


if __name__ == "__main__":
    run_phase_e_audit()
