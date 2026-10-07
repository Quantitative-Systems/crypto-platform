"""
PROJECT TOP1 — Chronological Validation (2023) & Out-of-Sample (2024-2026) Gating Engine.

Executes sequential, firewalled testing on all 9 Promising Development candidates:
Stage 1: Validation Testing (2023 Calendar Year) with frozen rules.
Stage 2: Out-of-Sample (OOS 2024-2026) Testing only for candidates surviving Validation.

Maintains absolute immutability and anti-p-hacking firewalls.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.oos_manager import OOSManager, OOSLockViolation
from research.discovery_lab.strategy_generator import StrategyExecutor
from research.discovery_lab.sync_dashboard_and_registry import sync_all

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
DISCOVERY_FILE = os.path.join(RESULTS_DIR, "autonomous_discovery_reports.json")
VAL_OOS_FILE = os.path.join(RESULTS_DIR, "validation_and_oos_results.json")


def run_validation_and_oos():
    print("=" * 90)
    print("PROJECT TOP1 — CHRONOLOGICAL VALIDATION (2023) & OOS (2024-2026) ENGINE")
    print("=" * 90)

    if not os.path.exists(DISCOVERY_FILE):
        print("ERROR: No autonomous discovery reports found!")
        return

    with open(DISCOVERY_FILE, "r") as f:
        all_reports = json.load(f)

    promising = [r for r in all_reports if r["status"] == "PROMISING"]
    print(f"Loaded {len(promising)} PROMISING Development candidates ready for Validation.")

    val_oos_records = []

    for cand in promising:
        cid = cand["candidate_id"]
        fam_method = [
            ("FAM-01-TREND", "run_family_1_trend_following"),
            ("FAM-02-PULLBACK", "run_family_2_trend_pullback"),
            ("FAM-03-BREAKOUT", "run_family_3_breakout"),
            ("FAM-04-MOMENTUM", "run_family_4_momentum"),
            ("FAM-05-MEANREV", "run_family_5_mean_reversion"),
            ("FAM-06-VOLEXP", "run_family_6_volatility_expansion"),
            ("FAM-07-MTFCONT", "run_family_7_mtf_continuation"),
            ("FAM-08-REGIME", "run_family_8_regime_adaptive"),
        ]
        method_name = dict(fam_method)[cand["family_id"]]
        symbol = cand["symbol"]
        set_name = cand["set"]
        sc = TIMEFRAME_SETS[set_name]

        print(f"\n======================================================================")
        print(f"TESTING CANDIDATE: {cid} ({cand['family_name']} on {symbol} {set_name})")
        print(f"Development Baseline: N={cand['n_trades']} | Net R={cand['net_r']:+.2f}R | Exp={cand['expectancy_r']:+.2f}R | PF={cand['profit_factor_r']}")
        print(f"======================================================================")

        htf = load_candles(symbol, sc["HTF"])
        mtf = load_candles(symbol, sc["MTF"])
        ltf = load_candles(symbol, sc["LTF"])

        # -------------------------------------------------------------
        # STAGE 1: VALIDATION (2023 CALENDAR YEAR)
        # -------------------------------------------------------------
        print(f"\n>>> Running Stage 1: VALIDATION (2023-01-01 to 2023-12-31 UTC)...")
        htf_val = OOSManager.get_validation_candles_by_date(htf, is_candidate_qualified=True, candidate_id=cid)
        mtf_val = OOSManager.get_validation_candles_by_date(mtf, is_candidate_qualified=True, candidate_id=cid)
        ltf_val = OOSManager.get_validation_candles_by_date(ltf, is_candidate_qualified=True, candidate_id=cid)

        executor_val = StrategyExecutor(
            symbol, set_name, htf_val, mtf_val, ltf_val,
            start_ts=OOSManager.VAL_START_TS, end_ts=OOSManager.VAL_END_TS
        )
        method_val = getattr(executor_val, method_name)
        res_val = method_val()

        val_trades = res_val["trades"]
        from research.analytics.r_accounting import RAccountingEngine
        m_val = res_val["metrics"]

        val_n = m_val["total_trades"]
        val_net_r = m_val["net_r"]
        val_exp_r = m_val["expectancy_r"]
        val_max_dd = m_val["max_drawdown_r"]
        val_pf = m_val["profit_factor_r"]
        val_top1_pct = m_val["top_1_pct_net_r"]

        val_passed = (val_exp_r > 0.0) and (val_net_r > 0.0) and (val_max_dd <= 25.0)

        print(f"  Validation 2023 Results: N={val_n:3d} | Net R={val_net_r:+6.2f}R | Exp={val_exp_r:+5.2f}R | PF={val_pf} | MaxDD={val_max_dd:5.2f}R | Top1={val_top1_pct:4.1f}%")
        print(f"  Validation Verdict: {'PASSED (Promoted to OOS)' if val_passed else 'FAILED (Degraded / Falsified)'}")

        # -------------------------------------------------------------
        # STAGE 2: OUT-OF-SAMPLE (2024-2026 UNSEEN DATA)
        # -------------------------------------------------------------
        oos_passed = False
        m_oos = {}
        if val_passed:
            print(f"\n>>> Running Stage 2: OUT-OF-SAMPLE (2024-01-01 to 2026-09-01 UTC)...")
            htf_oos = OOSManager.get_oos_candles_by_date(htf, is_candidate_validated=True, candidate_id=cid)
            mtf_oos = OOSManager.get_oos_candles_by_date(mtf, is_candidate_validated=True, candidate_id=cid)
            ltf_oos = OOSManager.get_oos_candles_by_date(ltf, is_candidate_validated=True, candidate_id=cid)

            executor_oos = StrategyExecutor(
                symbol, set_name, htf_oos, mtf_oos, ltf_oos,
                start_ts=OOSManager.OOS_START_TS, end_ts=1788307200  # up to Sept 2026
            )
            method_oos = getattr(executor_oos, method_name)
            res_oos = method_oos()

            m_oos = res_oos["metrics"]
            oos_n = m_oos["total_trades"]
            oos_net_r = m_oos["net_r"]
            oos_exp_r = m_oos["expectancy_r"]
            oos_max_dd = m_oos["max_drawdown_r"]
            oos_pf = m_oos["profit_factor_r"]
            oos_top1_pct = m_oos["top_1_pct_net_r"]

            oos_passed = (oos_exp_r > 0.0) and (oos_net_r > 0.0) and (oos_max_dd <= 25.0)

            print(f"  OOS 2024-2026 Results: N={oos_n:3d} | Net R={oos_net_r:+6.2f}R | Exp={oos_exp_r:+5.2f}R | PF={oos_pf} | MaxDD={oos_max_dd:5.2f}R | Top1={oos_top1_pct:4.1f}%")
            print(f"  OOS Verdict: {'QUALIFIED ROBUST (PASSED ALL GATES)' if oos_passed else 'FAILED OOS'}")
        else:
            print(f"  Stage 2 OOS testing LOCKED (Failed Validation prerequisite).")

        final_status = "QUALIFIED_ROBUST" if oos_passed else ("VALIDATED" if val_passed else "FAILED_VALIDATION")

        record = {
            "candidate_id": cid,
            "family_id": cand["family_id"],
            "family_name": cand["family_name"],
            "symbol": symbol,
            "set": set_name,
            "style": cand["style"],
            "dev_metrics": {
                "n": cand["n_trades"],
                "net_r": cand["net_r"],
                "exp_r": cand["expectancy_r"],
                "pf": cand["profit_factor_r"],
                "max_dd": cand["max_drawdown_r"],
            },
            "val_metrics": {
                "n": val_n,
                "net_r": val_net_r,
                "exp_r": val_exp_r,
                "pf": val_pf,
                "max_dd": val_max_dd,
                "passed": val_passed,
            },
            "oos_metrics": {
                "n": m_oos.get("total_trades", 0),
                "net_r": m_oos.get("net_r", 0.0),
                "exp_r": m_oos.get("expectancy_r", 0.0),
                "pf": m_oos.get("profit_factor_r", "N/A"),
                "max_dd": m_oos.get("max_drawdown_r", 0.0),
                "passed": oos_passed,
            },
            "final_status": final_status,
        }
        val_oos_records.append(record)

    # Save to file
    with open(VAL_OOS_FILE, "w") as f:
        json.dump(val_oos_records, f, indent=2)
    print(f"\nAll Validation & OOS results saved to: {VAL_OOS_FILE}")

    # Synchronize dashboard
    sync_all()


if __name__ == "__main__":
    run_validation_and_oos()
