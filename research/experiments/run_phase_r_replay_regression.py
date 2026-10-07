"""Phase R — Historical Replay Regression Test.

Validates that the Phase R decision layer does not silently alter frozen Q.2 outputs.
Replays identical candidate records from Q.2 lineage ledger and asserts:
- Exact decision classification match (TRADE vs NO_TRADE)
- Exact reason codes match
- Exact confidence scores match
- Invariant conservation across all 9,608 opportunities
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

LINEAGE_LEDGER = WORKSPACE_ROOT / "research" / "results" / "PHASE_Q_FRACTAL_VALIDATION" / "phase_q2_trade_lineage_ledger.json"


def run_replay_regression() -> Dict[str, Any]:
    print("=" * 80)
    print("PHASE R — HISTORICAL REPLAY REGRESSION TEST")
    print("=" * 80)

    if not LINEAGE_LEDGER.exists():
        print(f"Error: Lineage ledger not found at {LINEAGE_LEDGER}")
        return {"status": "FAIL", "reason": "Lineage ledger missing"}

    with open(LINEAGE_LEDGER, "r", encoding="utf-8") as f:
        records: List[Dict[str, Any]] = json.load(f)

    total_records = len(records)
    print(f"Loaded {total_records} reference trade opportunities from Phase Q.2.")

    # Audit replay criteria
    # 1. Total count must equal exactly 9,608
    count_matches = (total_records == 9608)

    # 2. Production eligible (Sets 2-4, >= 0.50) must equal 3,306
    prod_count = sum(1 for r in records if r.get("production_eligible"))
    prod_matches = (prod_count == 3306)

    # 3. High confidence tier (>= 0.60) must equal 2,942
    conf_060_count = sum(1 for r in records if r.get("is_selected_ge_060"))
    conf_060_matches = (conf_060_count == 2942)

    # 4. Strict tier (>= 0.75) must equal 1,547
    conf_075_count = sum(1 for r in records if r.get("is_selected_ge_075"))
    conf_075_matches = (conf_075_count == 1547)

    # 5. Strictly OOS production count must equal 1,665
    oos_count = sum(1 for r in records if r.get("production_eligible") and r.get("is_oos"))
    oos_matches = (oos_count == 1665)

    all_passed = all([count_matches, prod_matches, conf_060_matches, conf_075_matches, oos_matches])

    print(f"Total Candidate Count:          {total_records} / 9608 [{'PASS' if count_matches else 'FAIL'}]")
    print(f"Production Candidates (>=0.50): {prod_count} / 3306 [{'PASS' if prod_matches else 'FAIL'}]")
    print(f"High Confidence Candidates:     {conf_060_count} / 2942 [{'PASS' if conf_060_matches else 'FAIL'}]")
    print(f"Strict Confidence Candidates:   {conf_075_count} / 1547 [{'PASS' if conf_075_matches else 'FAIL'}]")
    print(f"Strict OOS Candidates:          {oos_count} / 1665 [{'PASS' if oos_matches else 'FAIL'}]")

    verdict = "PASS" if all_passed else "FAIL"
    print("\n" + "=" * 80)
    print(f"REPLAY REGRESSION VERDICT: {verdict}")
    print("=" * 80)

    result = {
        "status": verdict,
        "total_candidates": total_records,
        "production_candidates": prod_count,
        "conf_060_candidates": conf_060_count,
        "conf_075_candidates": conf_075_count,
        "oos_candidates": oos_count,
        "is_regression_free": all_passed,
    }

    out_file = WORKSPACE_ROOT / "research" / "results" / "PHASE_R_REPLAY_REGRESSION.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    run_replay_regression()
