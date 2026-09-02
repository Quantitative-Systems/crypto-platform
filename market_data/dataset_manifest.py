"""
Product 01 — Market Data: Immutable Dataset Manifest & Cryptographic Provenance Engine
Generates, validates, and registers SHA256 checksums, interval gap audits,
and multi-stage certification metadata for institutional quantitative datasets.
"""

import os
import sys
import json
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from market_data.data_manager import DataManager, CertificationState, CACHE_DIR, ALL_TIMEFRAMES, ALL_ASSETS
from market_intelligence.primitives import Candle


@dataclass
class DatasetManifest:
    manifest_id: str
    symbol: str
    venue: str  # e.g., Binance USDT-M Futures
    timeframe: str
    start_timestamp_utc: int
    end_timestamp_utc: int
    start_date_str: str
    end_date_str: str
    row_count: int
    duplicate_count: int
    missing_intervals: int
    maximum_gap_bars: int
    ohlcv_validation_passed: bool
    timezone: str
    source: str
    download_timestamp_utc: str
    sha256_checksum: str
    schema_version: str
    certification_status: str
    research_eligibility: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DatasetManifestManager:
    """
    Manages generation, verification, and persistence of immutable dataset manifests.
    """

    @staticmethod
    def compute_file_sha256(filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def generate_manifest_for_file(symbol: str, timeframe: str, filepath: str) -> Optional[DatasetManifest]:
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r") as f:
                raw = json.load(f)

            if not raw or not isinstance(raw, list):
                return None

            sha256_hash = DatasetManifestManager.compute_file_sha256(filepath)
            
            candles = [
                Candle(
                    timestamp=bar[0] // 1000,
                    open=float(bar[1]),
                    high=float(bar[2]),
                    low=float(bar[3]),
                    close=float(bar[4]),
                    volume=float(bar[5])
                )
                for bar in raw
            ]

            integrity = DataManager.validate_candle_integrity(candles, timeframe)
            cert_state, _ = DataManager.certify_dataset_pipeline(candles, timeframe, symbol)

            start_ts = candles[0].timestamp
            end_ts = candles[-1].timestamp
            start_str = datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            end_str = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            clean_sym = symbol.replace("/", "").upper()
            manifest_id = f"MANIFEST_{clean_sym}_{timeframe}_{start_ts}_{end_ts}"

            return DatasetManifest(
                manifest_id=manifest_id,
                symbol=symbol,
                venue="Binance USDT-M Futures",
                timeframe=timeframe,
                start_timestamp_utc=start_ts,
                end_timestamp_utc=end_ts,
                start_date_str=start_str,
                end_date_str=end_str,
                row_count=len(candles),
                duplicate_count=integrity.get("timestamp_violations", 0),
                missing_intervals=integrity.get("gaps_detected", 0),
                maximum_gap_bars=integrity.get("gaps_detected", 0),
                ohlcv_validation_passed=integrity.get("valid", False),
                timezone="UTC",
                source="Binance Official REST Archive",
                download_timestamp_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                sha256_checksum=sha256_hash,
                schema_version="v2.0-CANONICAL",
                certification_status=cert_state.value,
                research_eligibility=(cert_state == CertificationState.RESEARCH_ELIGIBLE)
            )
        except Exception:
            return None

    @staticmethod
    def audit_and_save_manifests(output_file: Optional[str] = None) -> List[DatasetManifest]:
        if output_file is None:
            output_file = os.path.join(os.path.dirname(__file__), "..", "scratch", "dataset_manifests.json")

        manifests: List[DatasetManifest] = []

        for asset in ALL_ASSETS:
            symbol = f"{asset}/USDT"
            clean_sym = symbol.replace("/", "").upper()
            for tf in ALL_TIMEFRAMES:
                candidates = [
                    os.path.join(CACHE_DIR, f"binance_{clean_sym}_{tf.lower()}.json"),
                    os.path.join(CACHE_DIR, f"binance_{clean_sym}_{tf}.json"),
                    os.path.join(CACHE_DIR, f"binance_{clean_sym}_{tf.upper()}.json")
                ]
                if tf == "1m":
                    candidates.insert(0, os.path.join(CACHE_DIR, f"binance_{clean_sym}_1min.json"))

                for c in candidates:
                    if os.path.exists(c):
                        m = DatasetManifestManager.generate_manifest_for_file(symbol, tf, c)
                        if m:
                            manifests.append(m)
                        break

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        data = {
            "total_datasets": len(manifests),
            "generated_timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manifests": [m.to_dict() for m in manifests]
        }
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        return manifests

    @staticmethod
    def print_manifest_summary(manifests: List[DatasetManifest]):
        print("=" * 125)
        print("MARKET DATA LAKE: IMMUTABLE DATASET MANIFEST & PROVENANCE REPORT")
        print("=" * 125)
        header = f"| {'Symbol':10s} | {'Timeframe':10s} | {'Rows':8s} | {'Start Date (UTC)':17s} | {'End Date (UTC)':17s} | {'SHA256 (Prefix)':16s} | {'Status':18s} | {'Eligible':8s} |"
        print(header)
        print("|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 10 + "|" + "-" * 19 + "|" + "-" * 19 + "|" + "-" * 18 + "|" + "-" * 20 + "|" + "-" * 10 + "|")
        for m in manifests:
            sha_short = m.sha256_checksum[:14] + ".."
            elig_str = "YES" if m.research_eligibility else "NO"
            print(f"| {m.symbol:10s} | {m.timeframe:10s} | {m.row_count:8d} | {m.start_date_str[:17]:17s} | {m.end_date_str[:17]:17s} | {sha_short:16s} | {m.certification_status:18s} | {elig_str:8s} |")
        print("=" * 125)


def main():
    manifests = DatasetManifestManager.audit_and_save_manifests()
    DatasetManifestManager.print_manifest_summary(manifests)


if __name__ == "__main__":
    main()
