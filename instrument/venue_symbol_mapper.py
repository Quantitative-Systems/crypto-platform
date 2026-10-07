"""Venue Symbol Mapper.

Translates between canonical engine symbols (BASE/QUOTE) and venue-specific
identifiers across major centralized and decentralized venues.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple
from instrument.symbol_normalizer import SymbolNormalizer


class VenueSymbolMapper:
    """Bidirectional symbol mapper for exchange integration."""

    @staticmethod
    def to_venue_symbol(canonical_symbol: str, venue: str) -> str:
        """Map canonical BASE/QUOTE symbol to venue's native ticker."""
        norm_sym, base, quote = SymbolNormalizer.normalize(canonical_symbol)
        v = venue.lower().strip()

        if v in ("binance", "bybit"):
            return f"{base}{quote}"
        elif v == "coinbase":
            return f"{base}-{quote}"
        elif v == "kraken":
            # Kraken native formatting
            if base == "BTC" and quote == "USD":
                return "XXBTZUSD"
            if base == "BTC" and quote == "EUR":
                return "XXBTZEUR"
            if base == "ETH" and quote == "USD":
                return "XETHZUSD"
            return f"{base}/{quote}"
        elif v == "okx":
            return f"{base}-{quote}"
        elif v == "deribit":
            if quote == "USD":
                return f"{base}-PERPETUAL"
            return f"{base}_{quote}"
        else:
            return f"{base}/{quote}"

    @staticmethod
    def to_canonical(venue_symbol: str, venue: str = "") -> str:
        """Map venue ticker back to canonical BASE/QUOTE."""
        canonical, _, _ = SymbolNormalizer.normalize(venue_symbol)
        return canonical
