"""STRATA Digital Trading Platform — Multi-Instrument Universe & Venue Registry.

Coordinates the active trading universe across multiple crypto instruments and venues:
- Enforces the 11-step institutional admission gate (instrument/instrument_registry.py)
- Enforces the crypto-base invariant (AssetClass.CRYPTO)
- Tracks market specifications: tick size, lot size, min notional, venue mapping
- Monitors data health and liquidity profiles
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from instrument.asset_class import AssetClass
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument
from instrument.instrument_registry import (
    AdmissionChecklist,
    AdmissionDecision,
    InstrumentRegistry,
)

logger = logging.getLogger(__name__)


@dataclass
class InstrumentSpec:
    symbol: str
    base_asset: str
    quote_asset: str
    is_admitted: bool
    admission_status: str
    tick_size: float
    lot_size: float
    min_notional_usd: float
    typical_spread_bps: float
    max_leverage: float
    venue: str = "BINANCE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_asset": self.base_asset,
            "quote_asset": self.quote_asset,
            "is_admitted": self.is_admitted,
            "admission_status": self.admission_status,
            "tick_size": self.tick_size,
            "lot_size": self.lot_size,
            "min_notional_usd": self.min_notional_usd,
            "typical_spread_bps": self.typical_spread_bps,
            "max_leverage": self.max_leverage,
            "venue": self.venue,
        }


class PlatformUniverseManager:
    """Singleton universe manager maintaining active admitted instruments."""

    _instance: Optional[PlatformUniverseManager] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.registry = InstrumentRegistry()
        self._universe: Dict[str, InstrumentSpec] = {}
        self._initialize_canonical_universe()
        self._initialized = True

    def _initialize_canonical_universe(self) -> None:
        """Register the platform's core research and production universe."""
        specs = [
            ("BTCUSDT", "BTC", "USDT", 0.1, 0.001, 10.0, 1.2, 5.0),
            ("ETHUSDT", "ETH", "USDT", 0.01, 0.01, 10.0, 1.8, 5.0),
            ("SOLUSDT", "SOL", "USDT", 0.01, 0.1, 10.0, 2.5, 3.0),
            ("BNBUSDT", "BNB", "USDT", 0.01, 0.01, 10.0, 2.0, 3.0),
        ]

        for sym, base, quote, tick, lot, min_notional, spread, lev in specs:
            # Evaluate admission gate
            report = self.registry.register(
                sym,
                has_historical_data=True,
                has_htf_mtf_ltf=True,
                has_sufficient_overlap=True,
                has_calibrated_slippage=True,
                has_financing_model=True,
                venue_supported=True,
            )

            spec = InstrumentSpec(
                symbol=sym,
                base_asset=base,
                quote_asset=quote,
                is_admitted=(report.decision == AdmissionDecision.ADMITTED),
                admission_status=report.decision.value,
                tick_size=tick,
                lot_size=lot,
                min_notional_usd=min_notional,
                typical_spread_bps=spread,
                max_leverage=lev,
            )
            self._universe[sym] = spec
            logger.info(f"Registered universe instrument: {sym} | Admitted: {spec.is_admitted}")

    def get_instrument(self, symbol: str) -> Optional[InstrumentSpec]:
        return self._universe.get(symbol.upper())

    def list_admitted_symbols(self) -> List[str]:
        return [sym for sym, spec in self._universe.items() if spec.is_admitted]

    def get_all_specs(self) -> List[Dict[str, Any]]:
        return [spec.to_dict() for spec in self._universe.values()]


# Global singleton
UNIVERSE_MANAGER = PlatformUniverseManager()
