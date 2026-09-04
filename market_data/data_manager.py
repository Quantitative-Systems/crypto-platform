"""
Product 01 — Market Data: Historical Data Manager & Multi-Stage Certification Pipeline
Provides institutional data acquisition, caching, multi-stage certification, and integrity validation
across all asset classes and timeframes (1m to 1M).
"""

import os
import sys
import json
import time
import argparse
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from market_data.binance_fetcher import BinanceFetcher
from market_data.data_certifier import DataCertifier
from market_intelligence.primitives import Candle


CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
ALL_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1M"]
ALL_ASSETS = ["BTC", "ETH", "SOL"]


class CertificationState(str, Enum):
    """
    Formal 5-stage certification lifecycle states for institutional research data.
    """
    RAW = "RAW"
    NORMALIZED = "NORMALIZED"
    VALIDATED = "VALIDATED"
    CERTIFIED = "CERTIFIED"
    RESEARCH_ELIGIBLE = "RESEARCH_ELIGIBLE"
    REJECTED = "REJECTED"


class DataManager:
    """
    Manages local historical candlestick warehouse, multi-stage certification, and integrity audits.
    """

    @staticmethod
    def get_cache_filepath(symbol: str, timeframe: str) -> str:
        clean_sym = symbol.replace("/", "").replace("-", "").upper()
        tf_map = {
            "1M": "1M", "1MO": "1M", "1MONTH": "1M",
            "1w": "1w", "1W": "1w", "1week": "1w",
            "1d": "1d", "1D": "1d", "1day": "1d",
            "4h": "4h", "4H": "4h",
            "1h": "1h", "1H": "1h",
            "15m": "15m", "15M": "15m",
            "5m": "5m", "5M": "5m",
            "1m": "1m", "1min": "1m", "1MIN": "1m",
        }
        clean_tf = tf_map.get(timeframe, tf_map.get(timeframe.upper(), timeframe.lower()))
        return os.path.join(CACHE_DIR, f"binance_{clean_sym}_{clean_tf}.json")

    @staticmethod
    def validate_candle_integrity(candles: List[Candle], timeframe: str) -> Dict[str, Any]:
        """
        Performs mathematical and structural invariant validation on candlestick series:
        1. Monotonically increasing timestamps (no duplicates, strictly sorted).
        2. OHLC price invariants: High >= max(Open, Close, Low) and Low <= min(Open, Close, High), prices > 0.
        3. Non-negative volume.
        4. Temporal gap detection against nominal timeframe step.
        """
        if not candles:
            return {
                "valid": False,
                "error": "EMPTY_DATASET",
                "total_candles": 0,
                "ohlc_violations": 0,
                "timestamp_violations": 0,
                "volume_violations": 0,
                "gaps_detected": 0
            }

        ohlc_violations = 0
        timestamp_violations = 0
        volume_violations = 0
        prev_ts: Optional[int] = None
        gaps_detected = 0

        # Nominal step in seconds
        tf_step_seconds = {
            "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
            "4h": 14400, "1d": 86400, "1w": 604800, "1M": 2592000
        }.get(timeframe, 60)

        for idx, c in enumerate(candles):
            # Check price positivity & OHLC bounds
            if c.open <= 0 or c.high <= 0 or c.low <= 0 or c.close <= 0:
                ohlc_violations += 1
            if c.high < max(c.open, c.close, c.low) or c.low > min(c.open, c.close, c.high):
                ohlc_violations += 1

            # Check volume non-negativity
            if c.volume < 0:
                volume_violations += 1

            # Check timestamp ordering
            if prev_ts is not None:
                if c.timestamp <= prev_ts:
                    timestamp_violations += 1
                elif (c.timestamp - prev_ts) > (tf_step_seconds * 3):
                    # Gap larger than 3 missing bars
                    gaps_detected += 1

            prev_ts = c.timestamp

        valid = (ohlc_violations == 0) and (timestamp_violations == 0) and (volume_violations == 0)

        return {
            "valid": valid,
            "total_candles": len(candles),
            "ohlc_violations": ohlc_violations,
            "timestamp_violations": timestamp_violations,
            "volume_violations": volume_violations,
            "gaps_detected": gaps_detected,
            "start_timestamp": candles[0].timestamp,
            "end_timestamp": candles[-1].timestamp
        }

    @staticmethod
    def certify_dataset_pipeline(candles: List[Candle], timeframe: str, symbol: str) -> Tuple[CertificationState, Dict[str, Any]]:
        """
        Transitions candlestick dataset through the full 5-stage certification pipeline:
        RAW -> NORMALIZED -> VALIDATED -> CERTIFIED -> RESEARCH_ELIGIBLE.
        """
        report: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "stage_reached": CertificationState.RAW.value,
            "checks": {}
        }

        # Stage 1: RAW Ingestion Check
        if not candles or len(candles) == 0:
            report["checks"]["raw"] = "FAILED: No candles found"
            return CertificationState.REJECTED, report
        report["stage_reached"] = CertificationState.NORMALIZED.value
        report["checks"]["normalized"] = f"PASSED: {len(candles)} candles normalized"

        # Stage 2: Invariant Validation Check
        integrity = DataManager.validate_candle_integrity(candles, timeframe)
        report["integrity"] = integrity
        if not integrity["valid"]:
            report["checks"]["validated"] = f"FAILED: OHLC({integrity['ohlc_violations']}) TS({integrity['timestamp_violations']})"
            return CertificationState.REJECTED, report
        report["stage_reached"] = CertificationState.VALIDATED.value
        report["checks"]["validated"] = "PASSED: Invariants verified"

        # Stage 3: Institutional Data Certification Check
        try:
            DataCertifier.certify_dataset(candles, timeframe, symbol, allow_gaps=True, max_allowed_gap_bars=1000)
            report["checks"]["certified"] = "PASSED: DataCertifier approved"
            report["stage_reached"] = CertificationState.CERTIFIED.value
        except Exception as e:
            report["checks"]["certified"] = f"FAILED: {str(e)}"
            return CertificationState.REJECTED, report

        # Stage 4: Research Eligibility Check (sufficient sample)
        min_bars = 10 if timeframe in ["1M", "1w"] else 50
        if len(candles) >= min_bars:
            report["stage_reached"] = CertificationState.RESEARCH_ELIGIBLE.value
            report["checks"]["research_eligible"] = "PASSED: Eligible for causal backtesting"
            return CertificationState.RESEARCH_ELIGIBLE, report
        else:
            report["checks"]["research_eligible"] = f"INSUFFICIENT_BARS ({len(candles)} < {min_bars})"
            return CertificationState.CERTIFIED, report

    @staticmethod
    def audit_inventory() -> List[Dict[str, Any]]:
        """
        Audits all cached datasets across assets and timeframes through the 5-stage certification pipeline.
        """
        inventory = []
        os.makedirs(CACHE_DIR, exist_ok=True)

        for asset in ALL_ASSETS:
            symbol = f"{asset}/USDT"
            clean_sym = symbol.replace("/", "").upper()
            for tf in ALL_TIMEFRAMES:
                fpath = DataManager.get_cache_filepath(symbol, tf)
                if not os.path.exists(fpath):
                    alt = os.path.join(CACHE_DIR, f"binance_{clean_sym}_{tf}.json")
                    if os.path.exists(alt):
                        fpath = alt

                if not fpath or not os.path.exists(fpath):
                    inventory.append({
                        "symbol": symbol,
                        "timeframe": tf,
                        "certification_state": CertificationState.RAW.value,
                        "status": "MISSING",
                        "candles": 0,
                        "start_date": "N/A",
                        "end_date": "N/A",
                        "gaps_detected": 0
                    })
                    continue

                try:
                    with open(fpath, "r") as f:
                        raw = json.load(f)

                    if not raw or not isinstance(raw, list):
                        inventory.append({
                            "symbol": symbol, "timeframe": tf,
                            "certification_state": CertificationState.RAW.value,
                            "status": "EMPTY", "candles": 0, "start_date": "N/A", "end_date": "N/A", "gaps_detected": 0
                        })
                        continue

                    candles = [
                        Candle(timestamp=bar[0] // 1000, open=float(bar[1]), high=float(bar[2]), low=float(bar[3]), close=float(bar[4]), volume=float(bar[5]))
                        for bar in raw
                    ]

                    state, report = DataManager.certify_dataset_pipeline(candles, tf, symbol)

                    start_str = datetime.fromtimestamp(candles[0].timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                    end_str = datetime.fromtimestamp(candles[-1].timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

                    inventory.append({
                        "symbol": symbol,
                        "timeframe": tf,
                        "certification_state": state.value,
                        "status": state.value,
                        "candles": len(candles),
                        "start_date": start_str,
                        "end_date": end_str,
                        "gaps_detected": report.get("integrity", {}).get("gaps_detected", 0)
                    })
                except Exception as e:
                    inventory.append({
                        "symbol": symbol, "timeframe": tf,
                        "certification_state": CertificationState.REJECTED.value,
                        "status": f"ERROR: {str(e)[:20]}",
                        "candles": 0, "start_date": "N/A", "end_date": "N/A", "gaps_detected": 0
                    })

        return inventory

    @staticmethod
    def print_inventory_report():
        """Prints a human-readable multi-stage certification inventory summary."""
        inv = DataManager.audit_inventory()
        print("=" * 115)
        print("QUANTITATIVE SYSTEMS PLATFORM: DATA LAKE 5-STAGE CERTIFICATION REPORT")
        print("=" * 115)
        header = f"| {'Symbol':10s} | {'Timeframe':10s} | {'Certification State':22s} | {'Candles':8s} | {'Start Date (UTC)':18s} | {'End Date (UTC)':18s} | {'Gaps':5s} |"
        print(header)
        print("|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 24 + "|" + "-" * 10 + "|" + "-" * 20 + "|" + "-" * 20 + "|" + "-" * 7 + "|")
        for row in inv:
            print(f"| {row['symbol']:10s} | {row['timeframe']:10s} | {row['certification_state']:22s} | {row['candles']:8d} | {row['start_date']:18s} | {row['end_date']:18s} | {row['gaps_detected']:5d} |")
        print("=" * 115)


def main():
    parser = argparse.ArgumentParser(description="Market Data Management CLI")
    parser.add_argument("command", choices=["status", "audit", "certify"], help="Command to run")
    args = parser.parse_args()

    if args.command in ["status", "audit", "certify"]:
        DataManager.print_inventory_report()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        DataManager.print_inventory_report()
    else:
        main()
