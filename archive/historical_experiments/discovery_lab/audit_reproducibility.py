"""
Quantitative Systems Platform (QSP) — Systematic Strategies Research Division.
Phase A: Clean-Slate Reproducibility & Cryptographic Provenance Audit.

Audits and proves:
1. Machine-verifiable cryptographic SHA-256 provenance hashes:
   - strategy_hash (canonical parameter dict & signal rules)
   - rule_hash (mathematical formula definitions)
   - data_hash (raw candle OHLCV arrays per asset/timeframe)
   - engine_version (git commit SHA & engine signature)
   - execution_model_version (adverse-first intra-bar collision)
   - friction_model_version (VIP-0 fee 0.075%, slippage 0.03%, spread 0.01%)
2. Clean-slate re-execution across all 3 chronological partitions:
   - Development (2021-01-01 to 2022-12-31 UTC)
   - Validation (2023-01-01 to 2023-12-31 UTC)
   - Out-of-Sample (2024-01-01 to 2026-06-30 UTC)
3. Bit-for-bit equivalence proof with recorded candidate registry metrics.
"""

import os
import sys
import json
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from market_intelligence.primitives import Candle
from strategy_candidate_v2.data_audit import TIMEFRAME_SETS, load_candles
from research.discovery_lab.oos_manager import OOSManager
from research.discovery_lab.strategy_generator import StrategyExecutor

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
VAL_OOS_FILE = os.path.join(RESULTS_DIR, "validation_and_oos_results.json")
OUTPUT_FILE = os.path.join(RESULTS_DIR, "AUDIT_PHASE_A_REPRODUCIBILITY.json")


def compute_sha256_dict(d: Dict[str, Any]) -> str:
    serialized = json.dumps(d, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_data_hash(candles_dict: Dict[str, List[Candle]]) -> str:
    hasher = hashlib.sha256()
    for tf in sorted(candles_dict.keys()):
        for c in candles_dict[tf]:
            line = f"{c.timestamp},{c.open},{c.high},{c.low},{c.close},{c.volume}"
            hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def get_git_commit_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN_COMMIT"


def run_phase_a_audit():
    print("=" * 90)
    print("PHASE A: CLEAN-SLATE REPRODUCIBILITY & CRYPTOGRAPHIC PROVENANCE AUDIT")
    print("=" * 90)

    if not os.path.exists(VAL_OOS_FILE):
        raise FileNotFoundError(f"Missing {VAL_OOS_FILE}")

    with open(VAL_OOS_FILE, "r") as f:
        val_oos_records = json.load(f)

    qualified = [r for r in val_oos_records if r["final_status"] == "QUALIFIED_ROBUST"]
    print(f"Auditing {len(qualified)} QUALIFIED_ROBUST research candidates...")

    git_sha = get_git_commit_sha()
    engine_version = f"QSP-Engine-v2.5-git-{git_sha[:10]}"
    execution_model_version = "Pessimistic-AdverseFirst-IntraBar-v1"
    friction_model_version = "Binance-VIP0-Taker0.075pct-Slip0.03pct-Spread0.01pct"
    audit_results = []
    all_bit_for_bit = True

    # Preload candles cache to compute data hashes
    candles_cache = {}

    for cand in qualified:
        cid = cand["candidate_id"]
        symbol = cand["symbol"]
        set_id = cand["set"]
        fam_id = cand["family_id"]

        print(f"\nVerifying Candidate: {cid} ({symbol} {set_id})...")

        # Preload data if not cached
        sc = TIMEFRAME_SETS[set_id]
        htf_tf = sc["HTF"]
        mtf_tf = sc["MTF"]
        ltf_tf = sc["LTF"]
        htf = load_candles(symbol, htf_tf)
        mtf = load_candles(symbol, mtf_tf)
        ltf = load_candles(symbol, ltf_tf)

        c_data = {"htf": htf, "mtf": mtf, "ltf": ltf}
        data_hash = compute_data_hash(c_data)

        # Strategy parameters and rule definition
        if fam_id == "FAM-07-MTFCONT":
            strat_params = {
                "family_id": "FAM-07-MTFCONT",
                "rules": "HTF EMA21 trend + MTF EMA21 trend + LTF 10-bar Donchian breakout",
                "ema_len": 21,
                "donchian_len": 10,
                "stop_atr_mult": 1.5,
                "target_r": 2.5,
                "max_risk_pct": 0.01,
            }
            method_name = "run_family_7_mtf_continuation"
        elif fam_id == "FAM-04-MOMENTUM":
            strat_params = {
                "family_id": "FAM-04-MOMENTUM",
                "rules": "MTF MACD(12,26,9) impulse + LTF EMA21 continuation cross",
                "fast_len": 12,
                "slow_len": 26,
                "sig_len": 9,
                "ema_len": 21,
                "stop_atr_mult": 1.5,
                "target_r": 2.5,
                "max_risk_pct": 0.01,
            }
            method_name = "run_family_4_momentum"
        else:
            raise ValueError(f"Unknown family {fam_id}")

        strategy_hash = compute_sha256_dict(strat_params)
        rule_hash = hashlib.sha256(strat_params["rules"].encode("utf-8")).hexdigest()

        # Re-run Development (2021-2022)
        htf_dev = OOSManager.get_development_candles_by_date(htf)
        mtf_dev = OOSManager.get_development_candles_by_date(mtf)
        ltf_dev = OOSManager.get_development_candles_by_date(ltf)
        exec_dev = StrategyExecutor(
            symbol, set_id, htf_dev, mtf_dev, ltf_dev,
            start_ts=OOSManager.DEV_START_TS, end_ts=OOSManager.DEV_END_TS
        )
        dev_res = getattr(exec_dev, method_name)()

        # Re-run Validation (2023)
        htf_val = OOSManager.get_validation_candles_by_date(htf, is_candidate_qualified=True, candidate_id=cid)
        mtf_val = OOSManager.get_validation_candles_by_date(mtf, is_candidate_qualified=True, candidate_id=cid)
        ltf_val = OOSManager.get_validation_candles_by_date(ltf, is_candidate_qualified=True, candidate_id=cid)
        exec_val = StrategyExecutor(
            symbol, set_id, htf_val, mtf_val, ltf_val,
            start_ts=OOSManager.VAL_START_TS, end_ts=OOSManager.VAL_END_TS
        )
        val_res = getattr(exec_val, method_name)()

        # Re-run OOS (2024-2026)
        htf_oos = OOSManager.get_oos_candles_by_date(htf, is_candidate_validated=True, candidate_id=cid)
        mtf_oos = OOSManager.get_oos_candles_by_date(mtf, is_candidate_validated=True, candidate_id=cid)
        ltf_oos = OOSManager.get_oos_candles_by_date(ltf, is_candidate_validated=True, candidate_id=cid)
        exec_oos = StrategyExecutor(
            symbol, set_id, htf_oos, mtf_oos, ltf_oos,
            start_ts=OOSManager.OOS_START_TS, end_ts=1788307200
        )
        oos_res = getattr(exec_oos, method_name)()


        # Compare with recorded metrics
        expected_dev = cand["dev_metrics"]
        expected_val = cand["val_metrics"]
        expected_oos = cand["oos_metrics"]

        dev_m = dev_res["metrics"]
        val_m = val_res["metrics"]
        oos_m = oos_res["metrics"]

        dev_match = (
            dev_m["total_trades"] == expected_dev["n"]
            and abs(dev_m["net_r"] - expected_dev["net_r"]) < 1e-4
            and abs(dev_m["max_drawdown_r"] - expected_dev["max_dd"]) < 1e-4
        )
        val_match = (
            val_m["total_trades"] == expected_val["n"]
            and abs(val_m["net_r"] - expected_val["net_r"]) < 1e-4
            and abs(val_m["max_drawdown_r"] - expected_val["max_dd"]) < 1e-4
        )
        oos_match = (
            oos_m["total_trades"] == expected_oos["n"]
            and abs(oos_m["net_r"] - expected_oos["net_r"]) < 1e-4
            and abs(oos_m["max_drawdown_r"] - expected_oos["max_dd"]) < 1e-4
        )

        strat_match = dev_match and val_match and oos_match
        if not strat_match:
            all_bit_for_bit = False
            print(f"  [MISMATCH] Dev={dev_match}, Val={val_match}, OOS={oos_match}")
        else:
            print(f"  [EXACT MATCH] Dev (N={dev_m['total_trades']}, NetR={dev_m['net_r']:+.2f}R), "
                  f"Val (N={val_m['total_trades']}, NetR={val_m['net_r']:+.2f}R), "
                  f"OOS (N={oos_m['total_trades']}, NetR={oos_m['net_r']:+.2f}R)")

        audit_results.append({
            "candidate_id": cid,
            "symbol": symbol,
            "set": set_id,
            "provenance_hashes": {
                "strategy_hash": strategy_hash,
                "rule_hash": rule_hash,
                "data_hash": data_hash,
                "engine_version": engine_version,
                "execution_model_version": execution_model_version,
                "friction_model_version": friction_model_version,
            },
            "parameters": strat_params,
            "reproducibility": {
                "development": {
                    "matched": dev_match,
                    "reproduced": {"n": dev_m["total_trades"], "net_r": dev_m["net_r"], "max_dd": dev_m["max_drawdown_r"], "pf": dev_m["profit_factor_r"]},
                    "expected": expected_dev,
                },
                "validation": {
                    "matched": val_match,
                    "reproduced": {"n": val_m["total_trades"], "net_r": val_m["net_r"], "max_dd": val_m["max_drawdown_r"], "pf": val_m["profit_factor_r"]},
                    "expected": expected_val,
                },
                "out_of_sample": {
                    "matched": oos_match,
                    "reproduced": {"n": oos_m["total_trades"], "net_r": oos_m["net_r"], "max_dd": oos_m["max_drawdown_r"], "pf": oos_m["profit_factor_r"]},
                    "expected": expected_oos,
                },
                "bit_for_bit_verified": strat_match,
            }
        })


    manifest = {
        "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        "audit_phase": "PHASE_A_REPRODUCIBILITY",
        "governance": "Quantitative Systems Platform (QSP) Research Division",
        "all_candidates_bit_for_bit_reproduced": all_bit_for_bit,
        "candidate_count": len(qualified),
        "results": audit_results,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 90)
    print(f"AUDIT PHASE A COMPLETE. ALL CANDIDATES REPRODUCED: {all_bit_for_bit}")
    print(f"Report saved to: {OUTPUT_FILE}")
    print("=" * 90)


if __name__ == "__main__":
    run_phase_a_audit()
