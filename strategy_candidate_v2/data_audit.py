"""
Data Availability Audit for Multi-Asset / Multi-Timeframe Strategy.

Produces the 18-combination data availability matrix:
  3 assets x 6 timeframe sets = 18 independent asset/set combinations.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.data_manager import DataManager
from market_intelligence.primitives import Candle


# Timeframe set definitions
TIMEFRAME_SETS = {
    "Set 1": {"HTF": "1M", "MTF": "1w", "LTF": "1d", "style": "Macro / Position"},
    "Set 2": {"HTF": "1w", "MTF": "1d", "LTF": "4h", "style": "Swing"},
    "Set 3": {"HTF": "1d", "MTF": "4h", "LTF": "1h", "style": "Swing / Intraday"},
    "Set 4": {"HTF": "4h", "MTF": "1h", "LTF": "15m", "style": "Intraday"},
    "Set 5": {"HTF": "1h", "MTF": "15m", "LTF": "5m", "style": "Short-Term Intraday"},
    "Set 6": {"HTF": "15m", "MTF": "5m", "LTF": "1m", "style": "Scalping"},
}

ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
MIN_WARMUP_CANDLES = 50


def load_candles(symbol: str, timeframe: str) -> Optional[List[Candle]]:
    """Load candles from cache."""
    try:
        fpath = DataManager.get_cache_filepath(symbol, timeframe)
        if not os.path.exists(fpath):
            return None
        with open(fpath, "r") as f:
            raw = json.load(f)
        if not raw or not isinstance(raw, list):
            return None
        candles = [
            Candle(
                timestamp=int(bar[0] // 1000),
                open=float(bar[1]),
                high=float(bar[2]),
                low=float(bar[3]),
                close=float(bar[4]),
                volume=float(bar[5]),
            )
            for bar in raw
        ]
        return candles
    except Exception:
        return None


def compute_data_gaps(candles: List[Candle], timeframe: str) -> List[Dict[str, Any]]:
    """Detect data gaps in a candle series."""
    tf_step_seconds = {
        "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
        "4h": 14400, "1d": 86400, "1w": 604800, "1M": 2592000,
    }.get(timeframe, 60)

    gaps = []
    if len(candles) < 2:
        return gaps

    for i in range(1, len(candles)):
        gap_seconds = candles[i].timestamp - candles[i - 1].timestamp
        if gap_seconds > tf_step_seconds * 1.5:
            gap_candles = int(gap_seconds / tf_step_seconds) - 1
            gaps.append({
                "start_ts": candles[i - 1].timestamp,
                "end_ts": candles[i].timestamp,
                "gap_seconds": gap_seconds,
                "estimated_missing_candles": max(0, gap_candles),
            })
    return gaps


def audit_single_combination(symbol: str, set_name: str) -> Dict[str, Any]:
    """Audit a single asset x set combination."""
    set_config = TIMEFRAME_SETS[set_name]
    htf_tf = set_config["HTF"]
    mtf_tf = set_config["MTF"]
    ltf_tf = set_config["LTF"]

    result = {
        "asset": symbol,
        "set": set_name,
        "style": set_config["style"],
        "htf_timeframe": htf_tf,
        "mtf_timeframe": mtf_tf,
        "ltf_timeframe": ltf_tf,
        "status": "UNKNOWN",
        "earliest_timestamp": None,
        "latest_timestamp": None,
        "earliest_date": None,
        "latest_date": None,
        "htf_candles": 0,
        "mtf_candles": 0,
        "ltf_candles": 0,
        "htf_gaps": [],
        "mtf_gaps": [],
        "ltf_gaps": [],
        "exchange": "Binance",
        "ohlcv_complete": False,
        "causal_reconstruction_possible": True,
        "sufficient_for_backtest": False,
        "data_quality": "UNKNOWN",
    }

    htf_candles = load_candles(symbol, htf_tf)
    mtf_candles = load_candles(symbol, mtf_tf)
    ltf_candles = load_candles(symbol, ltf_tf)

    if htf_candles is None or mtf_candles is None or ltf_candles is None:
        result["status"] = "MISSING_DATA"
        return result

    result["htf_candles"] = len(htf_candles)
    result["mtf_candles"] = len(mtf_candles)
    result["ltf_candles"] = len(ltf_candles)

    htf_start = htf_candles[0].timestamp
    htf_end = htf_candles[-1].timestamp
    mtf_start = mtf_candles[0].timestamp
    mtf_end = mtf_candles[-1].timestamp
    ltf_start = ltf_candles[0].timestamp
    ltf_end = ltf_candles[-1].timestamp

    overlap_start = max(htf_start, mtf_start, ltf_start)
    overlap_end = min(htf_end, mtf_end, ltf_end)

    result["earliest_timestamp"] = overlap_start
    result["latest_timestamp"] = overlap_end
    result["earliest_date"] = datetime.fromtimestamp(overlap_start, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    result["latest_date"] = datetime.fromtimestamp(overlap_end, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    def check_ohlcv(candles: List[Candle]) -> bool:
        for c in candles:
            if c.high < c.low or c.open <= 0 or c.close <= 0 or c.volume < 0:
                return False
            if c.high < max(c.open, c.close) or c.low > min(c.open, c.close):
                return False
        return True

    htf_ohlcv_ok = check_ohlcv(htf_candles)
    mtf_ohlcv_ok = check_ohlcv(mtf_candles)
    ltf_ohlcv_ok = check_ohlcv(ltf_candles)
    result["ohlcv_complete"] = htf_ohlcv_ok and mtf_ohlcv_ok and ltf_ohlcv_ok

    result["htf_gaps"] = compute_data_gaps(htf_candles, htf_tf)
    result["mtf_gaps"] = compute_data_gaps(mtf_candles, mtf_tf)
    result["ltf_gaps"] = compute_data_gaps(ltf_candles, ltf_tf)

    if overlap_start >= overlap_end:
        result["status"] = "NO_OVERLAP"
        result["usable_continuous_period"] = None
        return result

    htf_in_range = [c for c in htf_candles if overlap_start <= c.timestamp <= overlap_end]
    mtf_in_range = [c for c in mtf_candles if overlap_start <= c.timestamp <= overlap_end]
    ltf_in_range = [c for c in ltf_candles if overlap_start <= c.timestamp <= overlap_end]

    htf_warmup_ok = len(htf_in_range) >= MIN_WARMUP_CANDLES
    mtf_warmup_ok = len(mtf_in_range) >= MIN_WARMUP_CANDLES
    ltf_warmup_ok = len(ltf_in_range) >= MIN_WARMUP_CANDLES

    result["sufficient_for_backtest"] = (
        htf_warmup_ok and mtf_warmup_ok and ltf_warmup_ok and result["ohlcv_complete"]
    )

    total_gaps = len(result["htf_gaps"]) + len(result["mtf_gaps"]) + len(result["ltf_gaps"])
    if total_gaps == 0:
        result["data_quality"] = "EXCELLENT"
    elif total_gaps <= 3:
        result["data_quality"] = "GOOD"
    elif total_gaps <= 10:
        result["data_quality"] = "FAIR"
    else:
        result["data_quality"] = "POOR"

    result["status"] = "READY" if result["sufficient_for_backtest"] else "INSUFFICIENT_DATA"

    result["usable_continuous_period"] = {
        "start": result["earliest_date"],
        "end": result["latest_date"],
        "duration_days": (overlap_end - overlap_start) / 86400,
    }

    return result


def _ensure_usable_period(result):
    """Ensure usable_continuous_period exists for reporting."""
    if "usable_continuous_period" not in result or result["usable_continuous_period"] is None:
        result["usable_continuous_period"] = {
            "start": result.get("earliest_date"),
            "end": result.get("latest_date"),
            "duration_days": 0,
        }


def run_full_audit() -> List[Dict[str, Any]]:
    """Run the complete data availability audit."""
    results = []
    for symbol in ASSETS:
        for set_name in TIMEFRAME_SETS:
            result = audit_single_combination(symbol, set_name)
            results.append(result)
    return results


def print_audit_report(results: List[Dict[str, Any]]):
    """Print the data availability matrix."""
    print("=" * 160)
    print("DATA AVAILABILITY MATRIX - 3 ASSETS x 6 TIMEFRAME SETS = 18 COMBINATIONS")
    print("=" * 160)
    header = (
        f"| {'Asset':10s} | {'Set':6s} | {'HTF':5s} | {'MTF':5s} | {'LTF':5s} | "
        f"{'HTF #':>7s} | {'MTF #':>7s} | {'LTF #':>8s} | "
        f"{'Start Date':18s} | {'End Date':18s} | {'Duration':>10s} | "
        f"{'Status':16s} | {'Quality':8s} |"
    )
    print(header)
    print("|" + "-" * 12 + "|" + "-" * 8 + "|" + "-" * 7 + "|" + "-" * 7 + "|" + "-" * 7 + "|" +
          "-" * 9 + "|" + "-" * 9 + "|" + "-" * 10 + "|" +
          "-" * 20 + "|" + "-" * 20 + "|" + "-" * 12 + "|" +
          "-" * 18 + "|" + "-" * 10 + "|")

    for r in results:
        ucp = r.get("usable_continuous_period")
        duration_str = f"{ucp['duration_days']:.0f}d" if ucp else "N/A"
        print(
            f"| {r['asset']:10s} | {r['set']:6s} | {r['htf_timeframe']:5s} | {r['mtf_timeframe']:5s} | {r['ltf_timeframe']:5s} | "
            f"{r['htf_candles']:7d} | {r['mtf_candles']:7d} | {r['ltf_candles']:8d} | "
            f"{str(r['earliest_date'] or 'N/A'):18s} | {str(r['latest_date'] or 'N/A'):18s} | "
            f"{duration_str:>10s} | {r['status']:16s} | {r['data_quality']:8s} |"
        )

    print("=" * 160)
    print()

    ready_count = sum(1 for r in results if r["status"] == "READY")
    insufficient_count = sum(1 for r in results if r["status"] == "INSUFFICIENT_DATA")
    missing_count = sum(1 for r in results if r["status"] == "MISSING_DATA")
    no_overlap_count = sum(1 for r in results if r["status"] == "NO_OVERLAP")

    print(f"SUMMARY: {ready_count} READY | {insufficient_count} INSUFFICIENT_DATA | "
          f"{missing_count} MISSING_DATA | {no_overlap_count} NO_OVERLAP")
    print()

    print("DETAILED GAP REPORT:")
    for r in results:
        total_gaps = len(r["htf_gaps"]) + len(r["mtf_gaps"]) + len(r["ltf_gaps"])
        if total_gaps > 0:
            print(f"  {r['asset']} {r['set']}: {total_gaps} gaps detected")
            for gap in r["htf_gaps"]:
                start_str = datetime.fromtimestamp(gap["start_ts"], tz=timezone.utc).strftime("%Y-%m-%d")
                end_str = datetime.fromtimestamp(gap["end_ts"], tz=timezone.utc).strftime("%Y-%m-%d")
                print(f"    HTF gap: {start_str} -> {end_str} ({gap['estimated_missing_candles']} missing)")


if __name__ == "__main__":
    results = run_full_audit()
    print_audit_report(results)
    output_path = os.path.join(os.path.dirname(__file__), "data_audit_results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nDetailed results saved to {output_path}")
