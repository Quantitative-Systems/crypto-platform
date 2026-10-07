"""Phase Q.2 — Trade Lineage & Candidate-Level Audit Ledger.

Generates the exhaustive, 1-to-1 candidate lineage ledger across all 9,608 opportunities:
- event_id
- asset
- timestamp
- set_name
- hypothesis
- baseline_return_r
- fractal_confidence
- selection_status (>=0.50, >=0.60, >=0.75)
- exit_reason
- bars_held
Enables forensic verification of the asymmetric loss pruning mechanism.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_Q_FRACTAL_VALIDATION"
VAL_END_MS = 1720000000000  # July 2024 boundary


def build_lineage_ledger():
    stream_files = sorted(RESULTS_DIR.glob("FRAC_*.json"))
    lineage_records: List[Dict[str, Any]] = []

    for sf in stream_files:
        with open(sf, "r", encoding="utf-8") as f:
            sdata = json.load(f)

        symbol = sdata.get("symbol", "")
        set_name = sdata.get("set_name", "")
        hyp_type = sdata.get("hypothesis_type", "")

        for t in sdata.get("trades", []):
            entry_ts = int(t.get("entry_ts", 0))
            break_type = str(t.get("meta", {}).get("break_type", "UNKNOWN"))
            event_id = f"{symbol}_{set_name}_{entry_ts}_{break_type}"
            conf = float(t.get("meta", {}).get("confidence_score", 0.35))
            r_ret = float(t.get("realized_r", 0.0))

            is_sel_050 = conf >= 0.50
            is_sel_060 = conf >= 0.60
            is_sel_075 = conf >= 0.75
            is_oos = entry_ts > VAL_END_MS

            rec = {
                "lineage_id": f"LIN_{len(lineage_records):05d}",
                "event_id": event_id,
                "asset": symbol,
                "entry_ts": entry_ts,
                "exit_ts": int(t.get("exit_ts", 0)),
                "set_name": set_name,
                "hypothesis": hyp_type,
                "direction": int(t.get("direction", 1)),
                "entry_px": float(t.get("entry_px", 0.0)),
                "exit_px": float(t.get("exit_px", 0.0)),
                "baseline_return_r": r_ret,
                "exit_reason": str(t.get("exit_reason", "")),
                "bars_held": int(t.get("bars_held", 0)),
                "fractal_confidence": round(conf, 4),
                "fractal_alignment": str(t.get("meta", {}).get("fractal_alignment", "")),
                "fractal_bias": str(t.get("meta", {}).get("fractal_bias", "")),
                "is_selected_ge_050": is_sel_050,
                "is_selected_ge_060": is_sel_060,
                "is_selected_ge_075": is_sel_075,
                "is_oos": is_oos,
                "production_eligible": (set_name in ["SET_2", "SET_3", "SET_4"]) and is_sel_050,
            }
            lineage_records.append(rec)

    # Auditing
    total = len(lineage_records)
    n_050 = sum(1 for r in lineage_records if r["is_selected_ge_050"])
    n_060 = sum(1 for r in lineage_records if r["is_selected_ge_060"])
    n_075 = sum(1 for r in lineage_records if r["is_selected_ge_075"])
    n_prod = sum(1 for r in lineage_records if r["production_eligible"])
    n_prod_oos = sum(1 for r in lineage_records if r["production_eligible"] and r["is_oos"])

    # Loss pruning audit
    losses_all = [r for r in lineage_records if r["baseline_return_r"] < 0]
    losses_060 = [r for r in lineage_records if r["baseline_return_r"] < 0 and r["is_selected_ge_060"]]
    pruned_losses = [r for r in lineage_records if r["baseline_return_r"] < 0 and not r["is_selected_ge_060"]]

    avg_pruned_loss_r = float(np.mean([r["baseline_return_r"] for r in pruned_losses])) if pruned_losses else 0.0

    print("=" * 80)
    print("PHASE Q.2 — TRADE LINEAGE AUDIT LEDGER")
    print("=" * 80)
    print(f"Total Candidate Opportunities Mapped: {total}")
    print(f"Selected >= 0.50:                    {n_050}")
    print(f"Selected >= 0.60:                    {n_060}")
    print(f"Selected >= 0.75:                    {n_075}")
    print(f"Production Eligible (Sets 2-4, >=0.50): {n_prod}")
    print(f"Production Eligible Strictly OOS:    {n_prod_oos}")
    print(f"Pruned Losses under >=0.60:          {len(pruned_losses)} / {len(losses_all)} ({len(pruned_losses)/len(losses_all)*100:.1f}%)")
    print(f"Average Realized R of Pruned Losses: {avg_pruned_loss_r:.4f}R")

    # Save summary and sample
    summary_artifact = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_mapped_opportunities": total,
        "counts": {
            "unfiltered_baseline": total,
            "selected_ge_050": n_050,
            "selected_ge_060": n_060,
            "selected_ge_075": n_075,
            "production_eligible_sets_234": n_prod,
            "production_eligible_oos": n_prod_oos,
        },
        "loss_pruning": {
            "baseline_losses": len(losses_all),
            "retained_losses_060": len(losses_060),
            "pruned_losses_060": len(pruned_losses),
            "prune_rate_pct": round(len(pruned_losses) / len(losses_all) * 100.0, 2),
            "avg_pruned_loss_r": round(avg_pruned_loss_r, 4),
        },
        "sample_lineage_records": lineage_records[:15],
    }

    out_summary = RESULTS_DIR / "phase_q2_trade_lineage_summary.json"
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(summary_artifact, f, indent=2)

    out_full = RESULTS_DIR / "phase_q2_trade_lineage_ledger.json"
    with open(out_full, "w", encoding="utf-8") as f:
        json.dump(lineage_records, f)

    print(f"Lineage Summary saved to: {out_summary}")
    print(f"Full Lineage Ledger ({len(lineage_records)} records) saved to: {out_full}")
    print("=" * 80)


if __name__ == "__main__":
    build_lineage_ledger()
