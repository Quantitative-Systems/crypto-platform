"""Comprehensive Market Data Coverage, Quality, and Provenance Audit.

Audits all cached datasets across assets and timeframes:
1. Exact timestamp coverage (start, end, duration in days/years).
2. OHLC validity invariants (High >= max(O,C,L), Low <= min(O,C,H), prices > 0).
3. Monotonic timestamp checks (zero duplicates, strictly sorted).
4. Temporal gap detection (intervals exceeding nominal step * 3).
5. Volume non-negativity.
6. SHA-256 provenance hash per dataset.
7. Generates master data-quality report artifact.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

CACHE_DIR = WORKSPACE_ROOT / "market_data" / "cache"
OUTPUT_DIR = WORKSPACE_ROOT / "research" / "results" / "TRI_STRATEGY_FRACTAL_RESEARCH"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
TIMEFRAMES = ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]

NOMINAL_STEP_SECONDS = {
    "1M": 30 * 86400,
    "1w": 7 * 86400,
    "1d": 86400,
    "4h": 14400,
    "1h": 3600,
    "15m": 900,
    "3m": 180,
}


def compute_file_sha256(filepath: Path) -> str:
    if not filepath.exists():
        return "MISSING"
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def audit_single_dataset(symbol: str, timeframe: str) -> Dict[str, Any]:
    clean_sym = symbol.replace("/", "").replace("-", "").upper()
    cache_file = CACHE_DIR / f"binance_{clean_sym}_{timeframe}.json"

    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "filepath": str(cache_file.name),
        "exists": cache_file.exists(),
        "sha256": compute_file_sha256(cache_file),
        "total_candles": 0,
        "start_iso": None,
        "end_iso": None,
        "span_days": 0.0,
        "span_years": 0.0,
        "ohlc_violations": 0,
        "timestamp_violations": 0,
        "duplicate_timestamps": 0,
        "volume_violations": 0,
        "gaps_detected": 0,
        "max_gap_hours": 0.0,
        "status": "MISSING",
    }

    if not cache_file.exists():
        return result

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        result["status"] = f"CORRUPT_JSON: {e}"
        return result

    if not raw:
        result["status"] = "EMPTY"
        return result

    n = len(raw)
    result["total_candles"] = n

    step_sec = NOMINAL_STEP_SECONDS.get(timeframe, 60)
    prev_ts: Optional[int] = None
    seen_ts = set()
    ohlc_err = 0
    ts_err = 0
    dup_err = 0
    vol_err = 0
    first_ts: Optional[int] = None
    last_ts: Optional[int] = None
    gaps = 0
    max_gap_sec = 0.0

    for item in raw:
        if isinstance(item, list):
            ts = int(item[0])
            op = float(item[1])
            hi = float(item[2])
            lo = float(item[3])
            cl = float(item[4])
            vo = float(item[5]) if len(item) > 5 else 0.0
        elif isinstance(item, dict):
            ts = int(item.get("timestamp") or item.get("t") or item.get("open_time") or 0)
            op = float(item.get("open") or item.get("o") or 0)
            hi = float(item.get("high") or item.get("h") or 0)
            lo = float(item.get("low") or item.get("l") or 0)
            cl = float(item.get("close") or item.get("c") or 0)
            vo = float(item.get("volume") or item.get("v") or 0)
        else:
            continue

        if ts < 1e11:
            ts *= 1000

        if first_ts is None:
            first_ts = ts
        last_ts = ts

        # Invariant 1: OHLC price bounds
        if op <= 0 or hi <= 0 or lo <= 0 or cl <= 0:
            ohlc_err += 1
        if hi < max(op, cl, lo) or lo > min(op, cl, hi):
            ohlc_err += 1

        # Invariant 2: Non-negative volume
        if vo < 0:
            vol_err += 1

        # Invariant 3: Monotonic timestamps & duplicates
        if ts in seen_ts:
            dup_err += 1
        seen_ts.add(ts)

        if prev_ts is not None:
            if ts <= prev_ts:
                ts_err += 1
            else:
                delta_sec = (ts - prev_ts) / 1000
                if delta_sec > (step_sec * 3):
                    gaps += 1
                    if delta_sec > max_gap_sec:
                        max_gap_sec = delta_sec

        prev_ts = ts

    if first_ts is not None and last_ts is not None:
        dt_start = datetime.fromtimestamp(first_ts / 1000, tz=timezone.utc)
        dt_end = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc)
        span_d = (last_ts - first_ts) / (86400 * 1000)
        result["start_iso"] = dt_start.isoformat()
        result["end_iso"] = dt_end.isoformat()
        result["span_days"] = round(span_d, 1)
        result["span_years"] = round(span_d / 365.25, 2)

    result["ohlc_violations"] = ohlc_err
    result["timestamp_violations"] = ts_err
    result["duplicate_timestamps"] = dup_err
    result["volume_violations"] = vol_err
    result["gaps_detected"] = gaps
    result["max_gap_hours"] = round(max_gap_sec / 3600, 1)

    # Classify Status
    is_valid_data = (ohlc_err == 0 and ts_err == 0 and dup_err == 0 and vol_err == 0)
    if not is_valid_data:
        result["status"] = "INTEGRITY_VIOLATION"
    elif result["span_years"] >= 3.0:
        result["status"] = "RESEARCH_READY_MULTI_YEAR"
    elif result["span_days"] >= 30.0:
        result["status"] = "SHORT_WINDOW_INSUFFICIENT_FOR_MACRO"
    else:
        result["status"] = "TRUNCATED_MICRO_SAMPLE"

    return result


def run_full_data_audit():
    print("=" * 115)
    print("STRATA PHASE 1: COMPREHENSIVE DATA COVERAGE & INTEGRITY AUDIT")
    print("=" * 115)

    audit_matrix = {}
    summary_rows = []

    for sym in ASSETS:
        audit_matrix[sym] = {}
        for tf in TIMEFRAMES:
            res = audit_single_dataset(sym, tf)
            audit_matrix[sym][tf] = res
            summary_rows.append(res)

    # Print summary table
    header = f"{'SYMBOL':<10} | {'TF':<5} | {'CANDLES':<8} | {'START DATE':<12} | {'END DATE':<12} | {'SPAN (YRS)':<10} | {'GAPS':<5} | {'STATUS':<26}"
    print(header)
    print("-" * 115)

    for r in summary_rows:
        s_date = r["start_iso"][:10] if r["start_iso"] else "N/A"
        e_date = r["end_iso"][:10] if r["end_iso"] else "N/A"
        print(f"{r['symbol']:<10} | {r['timeframe']:<5} | {r['total_candles']:<8} | {s_date:<12} | {e_date:<12} | {r['span_years']:>10.2f} | {r['gaps_detected']:<5} | {r['status']:<26}")

    print("=" * 115)

    # Save artifact
    out_file = OUTPUT_DIR / "data_coverage_audit_report.json"
    report_data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "audit_version": "1.0.0-strata-phase1-coverage",
        "assets_audited": ASSETS,
        "timeframes_audited": TIMEFRAMES,
        "total_datasets": len(summary_rows),
        "results": audit_matrix,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"\nSaved Data Coverage Audit Report to: {out_file.name}")


if __name__ == "__main__":
    run_full_data_audit()
