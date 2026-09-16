"""
QCP Universal Market Data Fabric.
Institutional multi-venue, multi-instrument data abstraction unifying:
- Spot, Perpetual Swaps, Dated Futures
- Order book depth L2 distributions
- Funding rate & open interest time series
- Liquidation events and trade tick flow imbalance
- Deterministic SHA-256 provenance tracking
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class Venue(str):
    BINANCE = "BINANCE"
    OKX = "OKX"
    BYBIT = "BYBIT"
    COINBASE = "COINBASE"


class InstrumentType(str):
    SPOT = "SPOT"
    PERPETUAL = "PERPETUAL"
    DATED_FUTURES = "DATED_FUTURES"


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBookSnapshot:
    symbol: str
    venue: str
    timestamp_ms: int
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    data_provenance: str = "MEASURED"

    @property
    def mid_price(self) -> float:
        if self.bids and self.asks:
            return (self.bids[0].price + self.asks[0].price) / 2.0
        return 0.0

    @property
    def spread_bps(self) -> float:
        if self.bids and self.asks and self.mid_price > 0:
            return ((self.asks[0].price - self.bids[0].price) / self.mid_price) * 10000.0
        return 0.0

    @property
    def bid_depth_usd(self) -> float:
        return sum(b.price * b.size for b in self.bids[:10])

    @property
    def ask_depth_usd(self) -> float:
        return sum(a.price * a.size for a in self.asks[:10])

    @property
    def book_imbalance(self) -> float:
        total = self.bid_depth_usd + self.ask_depth_usd
        if total > 0:
            return (self.bid_depth_usd - self.ask_depth_usd) / total
        return 0.0


@dataclass
class FundingRateRecord:
    symbol: str
    venue: str
    timestamp_ms: int
    funding_rate_bps: float
    funding_interval_hours: int = 8
    annualized_rate_pct: float = field(init=False)

    def __post_init__(self):
        intervals_per_year = (365 * 24) / max(1, self.funding_interval_hours)
        self.annualized_rate_pct = (self.funding_rate_bps / 10000.0) * intervals_per_year * 100.0


@dataclass
class LiquidationEvent:
    symbol: str
    venue: str
    timestamp_ms: int
    side: str  # "BUY" (short liquidation) or "SELL" (long liquidation)
    price: float
    quantity: float
    usd_volume: float = field(init=False)

    def __post_init__(self):
        self.usd_volume = self.price * self.quantity


class UniversalMarketDataFabric:
    """
    Central institutional market data hub managing multi-venue feeds,
    funding metrics, depth snapshots, and data integrity certification.
    """

    def __init__(self, data_root: Optional[Path] = None, manifest_path: Optional[Path] = None):
        self.data_root = data_root or Path("/home/mrcn2/crypto-platform/market_data/cache")
        self.manifest_path = manifest_path
        self._cached_dfs: Dict[str, pd.DataFrame] = {}
        self._provenance_registry: Dict[str, str] = {}
        self._dataset_descriptors: Dict[str, Any] = {}

    def get_canonical_series(
        self,
        symbol: str,
        timeframe: str = "4h",
        venue: str = Venue.BINANCE,
        instrument: str = InstrumentType.SPOT,
    ) -> pd.DataFrame:
        """
        Loads a real, checksummed OHLCV series from the certified warehouse.

        Raises FileNotFoundError when the series does not exist. This fabric does
        NOT generate substitute candles: a missing dataset is an honest gap, not
        an invitation to simulate one.

        The certified loading path is delegated to the research evidence layer so
        that exactly ONE authoritative loader exists in the platform.
        """
        key = f"{venue}:{symbol}:{instrument}:{timeframe}".upper()
        if key in self._cached_dfs:
            return self._cached_dfs[key]

        from research.economic_evaluation_engine import CertifiedSeriesLoader

        loader = CertifiedSeriesLoader(cache_dir=self.data_root, manifest_path=self.manifest_path)
        df, descriptor = loader.load(symbol, timeframe)

        self._cached_dfs[key] = df
        self._provenance_registry[key] = descriptor.sha256
        self._dataset_descriptors[key] = descriptor
        return df

    def get_series_provenance(self, symbol: str, timeframe: str = "4h") -> Optional[Any]:
        """Returns the dataset provenance descriptor for a previously loaded series."""
        key = f"{Venue.BINANCE}:{symbol}:{InstrumentType.SPOT}:{timeframe}".upper()
        return self._dataset_descriptors.get(key)

    def get_order_book_snapshot(
        self,
        symbol: str,
        venue: str = Venue.BINANCE,
        reference_price: float = 100.0,
        depth_levels: int = 10,
        mode: str = "synthetic",
    ) -> Optional[OrderBookSnapshot]:
        """
        Returns an order-book depth snapshot.

        QCP has no historical or live L2 archive, so callers requesting mode="live"
        receive None — the platform reports that the data does not exist
        rather than inventing a book. A shape-only book is produced with
        mode="synthetic" for interface wiring tests; it is flagged SYNTHETIC and
        must never feed an economic claim.
        """
        if mode != "synthetic":
            return None

        spread_bps = 2.0
        half_spread = reference_price * (spread_bps / 20000.0)
        best_bid = reference_price - half_spread
        best_ask = reference_price + half_spread

        bids = [
            OrderBookLevel(price=round(best_bid * (1.0 - i * 0.0005), 4), size=round(10.0 + i * 5.0, 2))
            for i in range(depth_levels)
        ]
        asks = [
            OrderBookLevel(price=round(best_ask * (1.0 + i * 0.0005), 4), size=round(10.0 + i * 5.0, 2))
            for i in range(depth_levels)
        ]
        return OrderBookSnapshot(
            symbol=symbol,
            venue=venue,
            timestamp_ms=int(datetime.now(timezone.utc).timestamp() * 1000),
            bids=bids,
            asks=asks,
            data_provenance="SYNTHETIC",
        )

    def get_funding_rates(
        self,
        symbol: str,
        venue: str = Venue.BINANCE,
        lookback_intervals: int = 100,
        mode: str = "synthetic",
    ) -> List[FundingRateRecord]:
        """
        Returns historical 8h funding intervals.

        QCP holds no funding-rate archive, so callers requesting mode="live" receive
        an empty list and callers must treat funding-dependent alphas as
        DATA_UNAVAILABLE. mode="synthetic" exists for interface wiring.
        """
        if mode != "synthetic":
            return []

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        interval_ms = 8 * 3600 * 1000
        records: List[FundingRateRecord] = []
        for i in range(lookback_intervals):
            ts = now_ms - (lookback_intervals - i) * interval_ms
            rate_bps = 1.0 + 0.5 * np.sin(i / 10.0)
            records.append(FundingRateRecord(
                symbol=symbol,
                venue=venue,
                timestamp_ms=ts,
                funding_rate_bps=rate_bps,
                funding_interval_hours=8,
            ))
        return records

    def get_liquidation_events(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
        venue: str = Venue.BINANCE,
        mode: str = "live",
    ) -> List[LiquidationEvent]:
        """
        Returns liquidation prints within a window.

        No liquidation archive exists, so the default "live" mode returns an
        empty list. mode="synthetic" is for interface wiring only.
        """
        if mode != "synthetic":
            return []

        return [
            LiquidationEvent(
                symbol=symbol,
                venue=venue,
                timestamp_ms=start_ms + 3600000,
                side="SELL",
                price=150.0,
                quantity=100.0,
            ),
            LiquidationEvent(
                symbol=symbol,
                venue=venue,
                timestamp_ms=start_ms + 7200000,
                side="BUY",
                price=155.0,
                quantity=80.0,
            ),
        ]

    def get_data_availability(self) -> Dict[str, Any]:
        """
        Declares what data QCP actually holds. Used by the research factory and
        the orchestrator so unavailable-input alphas are reported honestly
        instead of being simulated.
        """
        return {
            "OHLCV": "AVAILABLE:Binance_archive_BTC_ETH_SOL_1m_to_1M",
            "ORDER_BOOK_L2": "UNAVAILABLE:no_historical_archive",
            "AGGRESSOR_FLOW": "UNAVAILABLE:no_historical_archive",
            "FUNDING_RATE_HISTORY": "UNAVAILABLE:no_historical_archive",
            "SPOT_PERP_BASIS": "UNAVAILABLE:no_historical_archive",
            "LIQUIDATIONS": "UNAVAILABLE:no_historical_archive",
            "WINDOWS_LOADED": sorted(self._dataset_descriptors.keys()),
        }

    def _compute_sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
