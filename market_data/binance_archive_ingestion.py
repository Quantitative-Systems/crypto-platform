"""
Quantitative Systems Platform (QSP) — Historical Archive Bulk Ingestion Engine.

Automates the acquisition, decompression, parsing, and caching of bulk historical klines
from Binance Public Vision Data Archives (data.binance.vision) for granular intervals (5M, 1M).
Enables historical backfill for 2021-2022 to unlock research for Set 5 and Set 6.
"""

import os
import sys
import json
import zipfile
import urllib.request
from io import BytesIO
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.data_manager import DataManager, CACHE_DIR
from market_data.primitives import Candle


class BinanceArchiveIngestion:
    """
    Downloads and ingests official monthly kline archives from data.binance.vision.
    """

    BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"

    @classmethod
    def get_archive_url(cls, symbol: str, timeframe: str, year: int, month: int) -> str:
        clean_sym = symbol.replace("/", "").replace("-", "").upper()
        clean_tf = timeframe.lower()
        filename = f"{clean_sym}-{clean_tf}-{year:04d}-{month:02d}.zip"
        return f"{cls.BASE_URL}/{clean_sym}/{clean_tf}/{filename}"

    @staticmethod
    def parse_csv_content(csv_text: str) -> List[List[Any]]:
        """Parses Binance Vision kline CSV into standard [timestamp, open, high, low, close, volume] format."""
        bars = []
        for line in csv_text.strip().split("\n"):
            if not line or line.startswith("open_time"):
                continue
            parts = line.split(",")
            if len(parts) >= 6:
                try:
                    open_time = int(parts[0])
                    o = float(parts[1])
                    h = float(parts[2])
                    l = float(parts[3])
                    c = float(parts[4])
                    v = float(parts[5])
                    bars.append([open_time, o, h, l, c, v])
                except (ValueError, IndexError):
                    continue
        return bars

    @classmethod
    def download_and_extract_month(
        cls,
        symbol: str,
        timeframe: str,
        year: int,
        month: int,
        timeout: int = 15,
    ) -> Optional[List[List[Any]]]:
        """Downloads a single monthly zip from Binance Vision and extracts raw kline rows."""
        url = cls.get_archive_url(symbol, timeframe, year, month)
        headers = {"User-Agent": "Mozilla/5.0 (Quantitative Systems Platform Archive Engine)"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    zip_data = response.read()
                    with zipfile.ZipFile(BytesIO(zip_data)) as z:
                        for filename in z.namelist():
                            if filename.endswith(".csv"):
                                with z.open(filename) as csv_file:
                                    csv_text = csv_file.read().decode("utf-8")
                                    return cls.parse_csv_content(csv_text)
        except Exception as e:
            # Network failure or 404
            return None
        return None

    @classmethod
    def merge_and_save_cache(
        cls,
        symbol: str,
        timeframe: str,
        new_bars: List[List[Any]],
    ) -> int:
        """Merges new bars with existing local cache and preserves chronological monotonicity."""
        cache_path = DataManager.get_cache_filepath(symbol, timeframe)
        existing_bars = []

        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    existing_bars = json.load(f)
            except Exception:
                existing_bars = []

        # Combine and deduplicate by open timestamp
        bar_dict = {}
        for b in existing_bars:
            bar_dict[b[0]] = b
        for b in new_bars:
            bar_dict[b[0]] = b

        merged = sorted(bar_dict.values(), key=lambda x: x[0])

        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(merged, f)

        return len(merged)

    @classmethod
    def backfill_years(
        cls,
        symbol: str,
        timeframe: str,
        start_year: int = 2021,
        end_year: int = 2022,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Backfills historical months across a calendar year range."""
        results = {"symbol": symbol, "timeframe": timeframe, "downloaded_months": [], "failed_months": []}
        all_bars = []

        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                url = cls.get_archive_url(symbol, timeframe, year, month)
                if dry_run:
                    results["downloaded_months"].append(f"{year}-{month:02d} (Dry Run: {url})")
                    continue

                bars = cls.download_and_extract_month(symbol, timeframe, year, month)
                if bars:
                    all_bars.extend(bars)
                    results["downloaded_months"].append(f"{year}-{month:02d} ({len(bars)} bars)")
                else:
                    results["failed_months"].append(f"{year}-{month:02d}")

        if all_bars and not dry_run:
            total_saved = cls.merge_and_save_cache(symbol, timeframe, all_bars)
            results["total_bars_in_cache"] = total_saved

        return results


if __name__ == "__main__":
    print("[INGESTION] Testing Binance Vision Archive dry-run resolution...")
    res = BinanceArchiveIngestion.backfill_years("SOL/USDT", "5m", 2021, 2022, dry_run=True)
    print(f"Target URLs resolved: {len(res['downloaded_months'])}")
    print(f"Sample URL: {res['downloaded_months'][0]}")
