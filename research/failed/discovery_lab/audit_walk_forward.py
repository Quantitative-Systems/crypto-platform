"""
Quantitative Systems Platform (QSP) — Systematic Strategies Research Division.
Phase D: Rolling Walk-Forward Analysis (WFA) & Efficiency Evaluation.

Tests whether strategy edges survive rolling market regimes across the 5.5-year history.
Window Architecture:
- 12-month In-Sample (IS) training / 6-month Out-of-Sample (OOS) testing
- Step size: 6 months rolling forward
- Zero test-set optimization (pure frozen parameter evaluation)
- Metrics: IS Net R, OOS Net R, OOS Trade Count, OOS Max Drawdown, and Walk-Forward Efficiency (WFE)
"""

import os
import sys
import json
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.strategy_generator import StrategyExecutor

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
VAL_OOS_FILE = os.path.join(RESULTS_DIR, "validation_and_oos_results.json")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "AUDIT_PHASE_D_WALK_FORWARD.json")

# Define 9 rolling 18-month windows (12M IS / 6M OOS)
WALK_FORWARD_WINDOWS = [
    {
        "window_id": "W1",
        "is_start": 1609459200,  # 2021-01-01
        "is_end": 1640995199,    # 2021-12-31
        "oos_start": 1640995200, # 2022-01-01
        "oos_end": 1656633599,   # 2022-06-30
    },
    {
        "window_id": "W2",
        "is_start": 1625097600,  # 2021-07-01
        "is_end": 1656633599,    # 2022-06-30
        "oos_start": 1656633600, # 2022-07-01
        "oos_end": 1672531199,   # 2022-12-31
    },
    {
        "window_id": "W3",
        "is_start": 1640995200,  # 2022-01-01
        "is_end": 1672531199,    # 2022-12-31
        "oos_start": 1672531200, # 2023-01-01
        "oos_end": 1688169599,   # 2023-06-30
    },
    {
        "window_id": "W4",
        "is_start": 1656633600,  # 2022-07-01
        "is_end": 1688169599,    # 2023-06-30
        "oos_start": 1688169600, # 2023-07-01
        "oos_end": 1704067199,   # 2023-12-31
    },
    {
        "window_id": "W5",
        "is_start": 1672531200,  # 2023-01-01
        "is_end": 1704067199,    # 2023-12-31
        "oos_start": 1704067200, # 2024-01-01
        "oos_end": 1719791999,   # 2024-06-30
    },
    {
        "window_id": "W6",
        "is_start": 1688169600,  # 2023-07-01
        "is_end": 1719791999,    # 2024-06-30
        "oos_start": 1719792000, # 2024-07-01
        "oos_end": 1735689599,   # 2024-12-31
    },
    {
        "window_id": "W7",
        "is_start": 1704067200,  # 2024-01-01
        "is_end": 1735689599,    # 2024-12-31
        "oos_start": 1735689600, # 2025-01-01
        "oos_end": 1751327999,   # 2025-06-30
    },
    {
        "window_id": "W8",
        "is_start": 1719792000,  # 2024-07-01
        "is_end": 1751327999,    # 2025-06-30
        "oos_start": 1751328000, # 2025-07-01
        "oos_end": 1767225599,   # 2025-12-31
    },
    {
        "window_id": "W9",
        "is_start": 1735689600,  # 2025-01-01
        "is_end": 1767225599,    # 2025-12-31
        "oos_start": 1767225600, # 2026-01-01
        "oos_end": 1788307200,   # 2026-09-01
    },
]


def run_phase_d_audit():
    print("=" * 90)
    print("PHASE D: ROLLING WALK-FORWARD ANALYSIS (WFA) & EFFICIENCY EVALUATION")
    print("=" * 90)

    if not os.path.exists(VAL_OOS_FILE):
        raise FileNotFoundError(f"Missing {VAL_OOS_FILE}")

    with open(VAL_OOS_FILE, "r") as f:
        val_oos_records = json.load(f)

    qualified = [r for r in val_oos_records if r["final_status"] == "QUALIFIED_ROBUST"]
    print(f"Evaluating 9 rolling walk-forward windows for {len(qualified)} QUALIFIED_ROBUST candidates...")

    audit_results = []

    for cand in qualified:
        cid = cand["candidate_id"]
        symbol = cand["symbol"]
        set_id = cand["set"]
        fam_id = cand["family_id"]

        sc = TIMEFRAME_SETS[set_id]
        htf = load_candles(symbol, sc["HTF"])
        mtf = load_candles(symbol, sc["MTF"])
        ltf = load_candles(symbol, sc["LTF"])

        method_name = "run_family_7_mtf_continuation" if fam_id == "FAM-07-MTFCONT" else "run_family_4_momentum"

        window_metrics = []
        positive_oos_windows = 0
        total_oos_net_r = 0.0

        for w in WALK_FORWARD_WINDOWS:
            wid = w["window_id"]

            # In-Sample Execution
            exec_is = StrategyExecutor(
                symbol, set_id, htf, mtf, ltf,
                start_ts=w["is_start"], end_ts=w["is_end"]
            )
            res_is = getattr(exec_is, method_name)()
            m_is = res_is["metrics"]

            # Out-of-Sample Execution
            exec_oos = StrategyExecutor(
                symbol, set_id, htf, mtf, ltf,
                start_ts=w["oos_start"], end_ts=w["oos_end"]
            )
            res_oos = getattr(exec_oos, method_name)()
            m_oos = res_oos["metrics"]

            is_net_r = round(float(m_is["net_r"]), 2)
            oos_net_r = round(float(m_oos["net_r"]), 2)
            oos_trades = int(m_oos["total_trades"])
            oos_max_dd = round(float(m_oos["max_drawdown_r"]), 2)

            # Annualized R: IS is 1 year (mult=1.0), OOS is 0.5 year (mult=2.0)
            is_ann_r = is_net_r
            oos_ann_r = oos_net_r * 2.0
            wfe = round(float(oos_ann_r / is_ann_r), 3) if is_ann_r > 0 else 0.0

            if oos_net_r > 0:
                positive_oos_windows += 1
            total_oos_net_r += oos_net_r

            window_metrics.append({
                "window_id": wid,
                "is_period": f"{datetime.fromtimestamp(w['is_start'], tz=timezone.utc).strftime('%Y-%m')} to {datetime.fromtimestamp(w['is_end'], tz=timezone.utc).strftime('%Y-%m')}",
                "oos_period": f"{datetime.fromtimestamp(w['oos_start'], tz=timezone.utc).strftime('%Y-%m')} to {datetime.fromtimestamp(w['oos_end'], tz=timezone.utc).strftime('%Y-%m')}",
                "is_net_r": is_net_r,
                "is_trades": int(m_is["total_trades"]),
                "oos_net_r": oos_net_r,
                "oos_trades": oos_trades,
                "oos_max_dd_r": oos_max_dd,
                "oos_pf": m_oos["profit_factor_r"],
                "wfe": wfe,
            })

        wfe_ratios = [w["wfe"] for w in window_metrics if w["wfe"] > 0]
        avg_wfe = round(float(np.mean(wfe_ratios)), 3) if wfe_ratios else 0.0

        print(f"\n{cid} ({symbol} {set_id}):")
        print(f"  Positive OOS Windows: {positive_oos_windows}/{len(WALK_FORWARD_WINDOWS)} ({positive_oos_windows/len(WALK_FORWARD_WINDOWS)*100:.1f}%)")
        print(f"  Cumulative OOS Net R: {total_oos_net_r:+.2f}R | Avg WFE: {avg_wfe}")

        audit_results.append({
            "candidate_id": cid,
            "symbol": symbol,
            "set": set_id,
            "positive_oos_windows": positive_oos_windows,
            "total_windows": len(WALK_FORWARD_WINDOWS),
            "oos_win_rate_pct": round((positive_oos_windows / len(WALK_FORWARD_WINDOWS)) * 100, 1),
            "cumulative_oos_net_r": round(total_oos_net_r, 2),
            "avg_walk_forward_efficiency": avg_wfe,
            "windows": window_metrics,
        })

    manifest = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_phase": "PHASE_D_WALK_FORWARD_ANALYSIS",
        "governance": "Quantitative Systems Platform (QSP) Research Division",
        "window_count": len(WALK_FORWARD_WINDOWS),
        "results": audit_results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 90)
    print("AUDIT PHASE D COMPLETE.")
    print(f"Report saved to: {OUTPUT_FILE}")
    print("=" * 90)


if __name__ == "__main__":
    run_phase_d_audit()
