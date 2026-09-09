"""
Target / Excursion Forensic Pre-Audit Script
Phase 1 & Phase 2 Analysis of Frozen COMPOSITE_01 Development Results

Examines all 13 trades in scratch/composite_01_dev_results.json:
- MFE (R), MAE (R), realized R, exit reason
- Timestamps (mfe_timestamp, exit_timestamp, duration)
- Peak-to-exit giveback (R and % of MFE)
- Excursion thresholds crossed: >= 1R, >= 2R, >= 2.5R, >= 3R
- Realized R vs excursion levels
- Runner convexity analysis (#05, #10, and all >= 1R trades)
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List

def run_forensic_audit(
    composite_path: str = "/home/mrcn2/crypto-platform/scratch/composite_01_dev_results.json"
):
    with open(composite_path, "r") as fp:
        data = json.load(fp)

    trades = data.get("all_trades", [])
    trades.sort(key=lambda x: x.get("entry_timestamp") or x.get("setup_timestamp") or 0)

    print(f"Loaded {len(trades)} trades from {composite_path}")

    rows = []
    
    # Threshold counters
    count_mfe_ge_1r = 0
    count_mfe_ge_2r = 0
    count_mfe_ge_2_5r = 0
    count_mfe_ge_3r = 0

    ge_1r_trades = []
    ge_2r_trades = []
    ge_2_5r_trades = []
    ge_3r_trades = []

    for idx, t in enumerate(trades, 1):
        trade_id = t.get("trade_id")
        stream_id = t.get("stream_id")
        symbol = t.get("symbol")
        direction = t.get("directional_permission", t.get("direction"))
        dir_label = "LONG" if "LONG" in str(direction) else "SHORT"
        
        mfe_r = float(t.get("mfe_r", 0.0))
        mae_r = float(t.get("mae_r", 0.0))
        realized_r = float(t.get("realized_r", t.get("realized_rr", 0.0)))
        exit_reason = t.get("exit_reason", "UNKNOWN")
        
        meta = t.get("metadata", {})
        mfe_ts = meta.get("mfe_timestamp") or t.get("mfe_timestamp")
        exit_ts = t.get("exit_timestamp")
        entry_ts = t.get("entry_timestamp")
        
        # Giveback in R
        # Peak-to-exit giveback: MFE_r - realized_r (for trades that had positive MFE)
        giveback_r = max(0.0, mfe_r - realized_r)
        giveback_pct = (giveback_r / mfe_r * 100.0) if mfe_r > 1e-4 else 0.0
        
        # Threshold checks
        exceeded_1r = (mfe_r >= 1.0)
        exceeded_2r = (mfe_r >= 2.0)
        exceeded_2_5r = (mfe_r >= 2.5)
        exceeded_3r = (mfe_r >= 3.0)

        if exceeded_1r:
            count_mfe_ge_1r += 1
            ge_1r_trades.append(trade_id)
        if exceeded_2r:
            count_mfe_ge_2r += 1
            ge_2r_trades.append(trade_id)
        if exceeded_2_5r:
            count_mfe_ge_2_5r += 1
            ge_2_5r_trades.append(trade_id)
        if exceeded_3r:
            count_mfe_ge_3r += 1
            ge_3r_trades.append(trade_id)

        # Realized R vs excursion levels
        # Was eventual realized R above or below each observed excursion level?
        # e.g., if trade reached 2.5R, was realized R >= 2.5R?
        realized_vs_1r = "ABOVE/AT" if realized_r >= 1.0 else "BELOW"
        realized_vs_2r = "ABOVE/AT" if realized_r >= 2.0 else "BELOW"
        realized_vs_2_5r = "ABOVE/AT" if realized_r >= 2.5 else "BELOW"
        realized_vs_3r = "ABOVE/AT" if realized_r >= 3.0 else "BELOW"

        row = {
            "index": idx,
            "trade_id": trade_id,
            "stream_id": stream_id,
            "symbol": symbol,
            "direction": dir_label,
            "entry_timestamp": entry_ts,
            "mfe_timestamp": mfe_ts,
            "exit_timestamp": exit_ts,
            "mfe_r": round(mfe_r, 4),
            "mae_r": round(mae_r, 4),
            "realized_r": round(realized_r, 4),
            "exit_reason": exit_reason,
            "giveback_r": round(giveback_r, 4),
            "giveback_pct": round(giveback_pct, 2),
            "exceeded_1r": exceeded_1r,
            "exceeded_2r": exceeded_2r,
            "exceeded_2_5r": exceeded_2_5r,
            "exceeded_3r": exceeded_3r,
            "realized_vs_1r": realized_vs_1r,
            "realized_vs_2r": realized_vs_2r,
            "realized_vs_2_5r": realized_vs_2_5r,
            "realized_vs_3r": realized_vs_3r,
        }
        rows.append(row)

    output_summary = {
        "total_trades": len(rows),
        "threshold_counts": {
            "mfe_ge_1r": count_mfe_ge_1r,
            "mfe_ge_2r": count_mfe_ge_2r,
            "mfe_ge_2_5r": count_mfe_ge_2_5r,
            "mfe_ge_3r": count_mfe_ge_3r
        },
        "trades_ge_1r": ge_1r_trades,
        "trades_ge_2r": ge_2r_trades,
        "trades_ge_2_5r": ge_2_5r_trades,
        "trades_ge_3r": ge_3r_trades,
        "rows": rows
    }

    out_file = "/home/mrcn2/crypto-platform/scratch/target_monetization_forensics.json"
    with open(out_file, "w") as fp:
        json.dump(output_summary, fp, indent=2)

    print("\n" + "="*80)
    print("TARGET / EXCURSION FORENSIC AUDIT COMPLETE")
    print(f"Total Trades: {len(rows)}")
    print(f"MFE >= 1.0R : {count_mfe_ge_1r} / {len(rows)} ({count_mfe_ge_1r/len(rows)*100:.1f}%)")
    print(f"MFE >= 2.0R : {count_mfe_ge_2r} / {len(rows)} ({count_mfe_ge_2r/len(rows)*100:.1f}%)")
    print(f"MFE >= 2.5R : {count_mfe_ge_2_5r} / {len(rows)} ({count_mfe_ge_2_5r/len(rows)*100:.1f}%)")
    print(f"MFE >= 3.0R : {count_mfe_ge_3r} / {len(rows)} ({count_mfe_ge_3r/len(rows)*100:.1f}%)")
    print("="*80)

    # Print markdown table of Phase 1
    print("\n| # | Trade ID | Stream | Dir | Entry | Init SL | Risk (USD) | 2.5R Level | MFE (R) | Realized R | Exit Reason | Giveback (R) | Giveback (%) | MFE >= 2.5R? | Realized >= 2.5R? |")
    print("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |")
    for r, t in zip(rows, trades):
        entry_p = float(t.get("entry_price", 0.0))
        stop_p = float(t.get("initial_stop_price", 0.0))
        risk_dist = abs(entry_p - stop_p)
        is_long = (r["direction"] == "LONG")
        level_2_5r = entry_p + 2.5 * risk_dist if is_long else entry_p - 2.5 * risk_dist
        print(f"| #{r['index']:02d} | `{r['trade_id']}` | {r['stream_id']} | {r['direction']} | {entry_p:.2f} | {stop_p:.2f} | {risk_dist:.2f} | {level_2_5r:.2f} | {r['mfe_r']:+.4f}R | {r['realized_r']:+.4f}R | `{r['exit_reason']}` | {r['giveback_r']:.4f}R | {r['giveback_pct']:.1f}% | {'YES' if r['exceeded_2_5r'] else 'NO'} | {r['realized_vs_2_5r']} |")

    return output_summary

if __name__ == "__main__":
    run_forensic_audit()
