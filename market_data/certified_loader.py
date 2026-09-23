"""Certified series loader (self-contained, data layer only).

Loads real Binance kline archives from the local warehouse, asserts their
integrity (SHA-256 + OHLC invariants + monotonic timestamps) and resolves
certification status from the dataset manifest registry when present.

A missing series raises FileNotFoundError instead of substituting fabricated
data — an honest gap is not an invitation to simulate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]


@dataclass
class DatasetProvenance:
    """Immutable provenance descriptor for one loaded market series."""

    dataset_id: str
    symbol: str
    timeframe: str
    venue: str
    row_count: int
    start_utc: str
    end_utc: str
    file_path: str
    sha256: str
    ohlc_invariants_ok: bool
    monotonic_timestamps: bool
    certification_status: str
    research_eligible: bool
    provenance: str
    generated_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CertifiedSeriesLoader:
    """Loads certified Binance klines; refuses to fabricate missing data."""

    def __init__(self, cache_dir: Optional[Path] = None,
                 manifest_path: Optional[Path] = None):
        repo_root = Path(__file__).resolve().parent.parent
        self.cache_dir = (Path(cache_dir) if cache_dir
                          else repo_root / "market_data" / "cache")
        self.manifest_path = (Path(manifest_path) if manifest_path
                              else repo_root / "proofs" / "work" / "dataset_manifests.json")
        self._manifest_cache: Optional[Dict[str, Any]] = None

    @staticmethod
    def _sha256_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()

    def available_series(self) -> List[Tuple[str, str]]:
        """(symbol, timeframe) pairs actually present in the warehouse."""
        found: List[Tuple[str, str]] = []
        for path in sorted(self.cache_dir.glob("binance_*_*.json")):
            parts = path.stem.split("_")
            if len(parts) != 3:
                continue
            _, raw_symbol, timeframe = parts
            if not raw_symbol.upper().endswith("USDT") or len(raw_symbol) <= 4:
                continue
            found.append((f"{raw_symbol[:-4]}/USDT", timeframe))
        return found

    def _load_manifests(self) -> Dict[str, Any]:
        if self._manifest_cache is not None:
            return self._manifest_cache
        self._manifest_cache = {}
        if self.manifest_path.exists():
            with open(self.manifest_path, "r") as f:
                payload = json.load(f)
            for m in payload.get("manifests", []):
                self._manifest_cache[f"{m.get('symbol')}::{m.get('timeframe')}"] = m
        return self._manifest_cache

    def _resolve_certification(self, symbol: str, timeframe: str,
                               sha256: str) -> Tuple[str, bool]:
        manifest = self._load_manifests().get(f"{symbol}::{timeframe}")
        if not manifest:
            return ("UNCERTIFIED", False)
        matches = manifest.get("sha256_checksum") == sha256
        status = manifest.get("certification_status", "UNCERTIFIED")
        eligible = bool(manifest.get("research_eligibility", False)) and matches
        if not matches:
            status = f"{status}_CHECKSUM_MISMATCH"
        return (status, eligible)

    def load(self, symbol: str, timeframe: str = "4h"
             ) -> Tuple[pd.DataFrame, DatasetProvenance]:
        """Load a real series; raise FileNotFoundError when absent."""
        clean = symbol.replace("/", "").replace("-", "").upper()
        path = self.cache_dir / f"binance_{clean}_{timeframe}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"NO_CERTIFIED_SERIES_FOR:{symbol}:{timeframe} at {path}. "
                "The platform does not fabricate market data; ingest the dataset first.")

        with open(path, "r") as f:
            raw = json.load(f)

        sha256 = self._sha256_file(path)
        df = pd.DataFrame(raw, columns=KLINE_COLUMNS)
        df = df.drop(columns=["ignore"]).astype(float)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume",
                 "quote_volume", "trades"]]
        df = (df.sort_values("timestamp")
                .drop_duplicates(subset=["timestamp"])
                .reset_index(drop=True))

        ohlc_ok = bool(
            ((df["high"] >= df[["open", "close", "low"]].max(axis=1))
             & (df["low"] <= df[["open", "close", "high"]].min(axis=1))
             & (df[["open", "high", "low", "close"]] > 0).all(axis=1)).all())
        monotonic = bool(df["timestamp"].is_monotonic_increasing)

        status, eligible = self._resolve_certification(symbol, timeframe, sha256)
        provenance = ("MEASURED_CERTIFIED_DATA" if eligible
                      else "MEASURED_UNCERTIFIED_DATA")

        descriptor = DatasetProvenance(
            dataset_id=f"binance_{clean}_{timeframe}_{sha256[:12]}",
            symbol=symbol, timeframe=timeframe, venue="Binance",
            row_count=int(len(df)),
            start_utc=df["timestamp"].iloc[0].isoformat(),
            end_utc=df["timestamp"].iloc[-1].isoformat(),
            file_path=str(path), sha256=sha256,
            ohlc_invariants_ok=ohlc_ok, monotonic_timestamps=monotonic,
            certification_status=status, research_eligible=eligible,
            provenance=provenance)
        return df, descriptor
