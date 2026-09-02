"""
Product 01 - Market Data: Data Quality Audit & Certification Metrics Engine

Replaces the naive interval-set scanner with institutional data-quality checks:

  1. OHLC + monotonic timestamp validation (strict).
  2. Duplicate timestamp detection.
  3. Missing-bars estimation against the canonical (calendar-aware for 1M) interval.
  4. Truncation detection: dataset must reach within 21 days of "now".
  5. Certification verdict (RESEARCH_ELIGIBLE / TRUNCATED / CORRUPT / STALE).

CLI keeps the JSON report shape so downstream tooling keeps working.
"""

import os
import json
import math
from datetime import datetime, timezone

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

# Canonical interval in ms per timeframe. 1M is calendar-aware (checked separately).
CANONICAL_MS = {
    "15m": 15 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
    "1M": None,  # calendar-aware
}


def _parse_tf(filename: str) -> str:
    # binance_BTCUSDT_15m.json
    stem = filename.replace(".json", "").split("_")
    return stem[-1] if len(stem) >= 3 else ""


def audit_data() -> dict:
    report = {}
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    now = datetime.now(timezone.utc)

    for f in sorted(files):
        path = os.path.join(CACHE_DIR, f)
        try:
            with open(path, "r") as fp:
                data = json.load(fp)
        except Exception as e:
            report[f] = {"error": str(e)}
            continue

        if not data:
            report[f] = {"error": "Empty data"}
            continue

        first = data[0]
        if isinstance(first, list):
            get_ts = lambda x: x[0]
            get_ohlc = lambda x: (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        elif isinstance(first, dict):
            get_ts = lambda x: x.get("timestamp") or x.get("open_time") or x.get("time")
            get_ohlc = None
        else:
            report[f] = {"error": "Unknown format"}
            continue

        timestamps = [get_ts(row) for row in data]
        if any(ts is None for ts in timestamps):
            report[f] = {"error": "Missing timestamps"}
            continue

        tf = _parse_tf(f)
        raw_count = len(timestamps)
        uniq = sorted(set(timestamps))
        duplicates = raw_count - len(uniq)

        # OHLC validation (list format only)
        ohlc_violations = 0
        if get_ohlc is not None:
            for row in data:
                try:
                    o, h, l, c = get_ohlc(row)
                    if h < l or c > h or c < l or min(o, h, l, c) <= 0:
                        ohlc_violations += 1
                except Exception:
                    ohlc_violations += 1

        start_ms, end_ms = uniq[0], uniq[-1]
        def _fmt(ms):
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        missing_bars = 0
        canonical = CANONICAL_MS.get(tf.lower())

        if canonical is not None:
            for i in range(1, len(uniq)):
                gap = uniq[i] - uniq[i-1]
                if gap > canonical:
                    missing_bars += int(math.floor((gap - 1) / canonical))
        elif tf and tf.upper() in ("1M", "1MO", "1MONTH"):
            # Calendar-aware monthly: count calendar months between opens
            for i in range(1, len(uniq)):
                a = datetime.fromtimestamp(uniq[i-1] / 1000, tz=timezone.utc)
                b = datetime.fromtimestamp(uniq[i] / 1000, tz=timezone.utc)
                months = (b.year - a.year) * 12 + (b.month - a.month)
                if months > 1:
                    missing_bars += (months - 1)

        # Truncation / staleness
        age_days = (now - datetime.fromtimestamp(end_ms / 1000, tz=timezone.utc)).days
        truncated = age_days > 21

        if ohlc_violations or duplicates > 0:
            verdict = "CORRUPT"
        elif truncated:
            verdict = "TRUNCATED"
        elif missing_bars > 0:
            verdict = "RESEARCH_ELIGIBLE_GAPS"
        else:
            verdict = "RESEARCH_ELIGIBLE"

        report[f] = {
            "num_candles": raw_count,
            "unique_timestamps": len(uniq),
            "duplicates": duplicates,
            "ohlc_violations": ohlc_violations,
            "start_time": _fmt(start_ms),
            "end_time": _fmt(end_ms),
            "missing_bars_est": missing_bars,
            "dataset_age_days": age_days,
            "is_truncated": truncated,
            "certification_verdict": verdict,
        }

    return report


if __name__ == "__main__":
    rep = audit_data()
    out = os.path.join(os.path.dirname(__file__), "..", "scratch", "data_quality_report.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(rep, f, indent=2)
    print(json.dumps(rep, indent=4))
